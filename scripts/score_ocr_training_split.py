"""Score saved train-split inference and render train/validation tables; no fine-tuning."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.crop_scoring import (
    build_report, canonical_text, freeze_manifest, load_run, normalise_text, write_report,
)
from backend.app.evaluation.metrics import edit_distance
from backend.app.evaluation.review_decisions import digest, load_source, validate_text, write_rows
from scripts.prepare_ocr_template_tables import prepare


def diagnostic(rows, predictions, model):
    summary, details = [], []
    for mode, transform in (("raw", canonical_text), ("normalised", normalise_text)):
        local = []
        for row in rows:
            p = predictions.get(row['review_id'])
            status = p['status'] if p else 'missing'
            ref = transform(row['transcription'])
            hypothesis = transform(p['raw_text']) if status == 'success' else ''
            local.append(dict(model=model, split='train', scoring_mode=mode, input_set='annotation',
                              review_id=row['review_id'], field=row['label'], reference=ref, hypothesis=hypothesis,
                              prediction_status=status, character_errors=edit_distance(ref,hypothesis),
                              reference_characters=len(ref), word_errors=edit_distance(ref.split(),hypothesis.split()),
                              reference_words=len(ref.split()), exact=ref==hypothesis, verified_benchmark=False))
        details.extend(local)
        for field in ('front_eds_num','front_eds_destination','front_eds_route','all_fields_micro'):
            chosen = [r for r in local if field=='all_fields_micro' or r['field']==field]
            count=len(chosen); chars=sum(r['reference_characters'] for r in chosen); words=sum(r['reference_words'] for r in chosen)
            ce=sum(r['character_errors'] for r in chosen); we=sum(r['word_errors'] for r in chosen); exact=sum(r['exact'] for r in chosen)
            summary.append(dict(model=model, split='train', scoring_mode=mode, input_set='annotation', field=field,
                                candidate_crops=count, cer_pct=100*ce/chars if chars else None,
                                wer_pct=100*we/words if words else None, exact_match_pct=100*exact/count if count else None,
                                character_errors=ce, reference_characters=chars, word_errors=we, reference_words=words,
                                exact_count=exact, failed_or_missing=sum(r['prediction_status']!='success' for r in chosen),
                                verified_benchmark=False))
    return summary, details


def run(args):
    out=args.output
    if out.exists():
        raise FileExistsError(out)
    paths=[args.training_review,args.validation_review,args.validation_config,args.validation_summary]
    input_hashes={str(p):digest(p) for p in paths}
    _, original_train=load_source(args.training_review)
    train=[]
    for source in original_train:
        row=dict(source,crop_source='annotation')
        reason=row.get('training_exclusion_reason','')
        if row.get('training_disposition')=='quarantined_legacy_holdout_candidate':
            reason=reason or 'Legacy holdout quarantine remains unresolved'
        if reason and reason not in row.get('exclusion_reason',''):
            row['exclusion_reason']='; '.join(filter(None,[row.get('exclusion_reason'),reason]))
        train.append(row)
    candidates=[r for r in train if r['legibility']=='full' and r['field_status']=='present'
                and not r.get('exclusion_reason') and r.get('field_review_status')!='needs_resolution']
    for row in candidates:
        validate_text(row['transcription'],row['legibility'],row['field_status'])
    if not candidates:
        raise ValueError('No provisional train label candidates')
    inventory={r['review_id']:r for r in train}
    config=json.loads(args.validation_config.read_text())
    run_paths={'easyocr':args.easyocr_run,'trocr':args.trocr_run,'paddleocr':args.paddleocr_run}
    combined_config={'models':[]}
    summaries=[];details=[];identities={};execution={}
    for model in config['models']:
        mid=model['id']; run=run_paths[mid]
        predictions,identity=load_run(run,inventory)
        if identity.get('split')!='train' or identity['engine']!=mid:
            raise ValueError('Wrong train run split/model')
        if set(predictions)!=set(inventory):
            raise ValueError('Training run does not retain the entire requested inventory')
        valid_path=(args.validation_config.resolve().parent/model['baseline']['run_dir']).resolve()
        valid_report=json.loads((valid_path/'report.json').read_text())
        if (identity['model_sha256_before']!=identity['model_sha256_after']
                or identity['model_sha256_before']!=valid_report['model_sha256_before']):
            raise ValueError('Train/validation pretrained checkpoint hashes differ')
        identities[mid]=identity
        candidate_ids={r['review_id'] for r in candidates}
        execution[mid]=dict(retained_records=len(predictions),
                            policy_skips=sum(bool(inventory[rid].get('exclusion_reason')) for rid in predictions),
                            successful_recognitions=sum(p['status']=='success' for p in predictions.values()),
                            failed_scored_candidates=sum(predictions[rid]['status']!='success' for rid in candidate_ids),
                            engine_failures_in_scored_candidates=sum(predictions[rid]['status']!='success' and bool(predictions[rid].get('line_count')) for rid in candidate_ids),
                            actual_device=identity['actual_device'])
        s,d=diagnostic(candidates,predictions,mid);summaries.extend(s);details.extend(d)
        combined_config['models'].append(dict(id=mid,baseline={'runs':[
            dict(run_dir=str(run.resolve()),splits=['train'],input_sets=['annotation']),
            dict(model['baseline'],run_dir=str(valid_path))]}))
    if len({x['frozen_line_layout']['sha256'] for x in identities.values()})!=1:
        raise ValueError('Training models did not use identical frozen input geometry')
    with args.validation_summary.open(newline='') as f:
        validation=[dict(r,split='valid') for r in csv.DictReader(f)]
    combined=[*validation,*summaries]
    out.mkdir(parents=True)
    write_rows(out/'train.review.csv',list(dict.fromkeys(k for r in train for k in r)),train)
    manifest=freeze_manifest([out/'train.review.csv',args.validation_review])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'comparison.json').write_text(json.dumps(combined_config,indent=2)+'\n')
    report=build_report(manifest,combined_config,out)
    write_report(report,out/'official')
    columns=list(dict.fromkeys(k for r in combined for k in r))
    write_rows(out/'combined_diagnostic_summary.csv',columns,combined)
    write_rows(out/'training_diagnostic_summary.csv',list(summaries[0]),summaries)
    write_rows(out/'training_diagnostic_outcomes.csv',list(details[0]),details)
    tables=out/'tables'
    prepare(args.training_manifest,args.validation_manifest,out/'official/report.json',tables,
            out/'combined_diagnostic_summary.csv')
    audit=dict(purpose='Pretrained OCR evaluation on training-split crops, not model fine-tuning',
               input_sha256=input_hashes,inventory=len(train),candidate_count=len(candidates),
               candidate_field_counts=dict(Counter(r['label'] for r in candidates)),
               candidate_ids=[r['review_id'] for r in candidates],
               policy_excluded_before_inference=sum(bool(r.get('exclusion_reason')) for r in train),
               run_identities=identities,execution=execution,
               official_eligible=sum(r['scoring_eligible'] for r in manifest['rows']),
               reference_matching_used=False,weights_updated=False,test_images_accessed=False,
               limits=['AI labels remain provisional; official eligibility gates unchanged.',
                       'These are scores on the designated training split, not held-out final-test accuracy; these runs did not update model weights.',
                       'Train uses unreviewed frozen automatic geometry; validation used earlier AI-reviewed geometry.',
                       'Devices differ across engine/split runs as recorded in their identities. EasyOCR uses its native CPU quantisation defaults. Do not rank mixed-device latency or attribute split differences solely to learning.'])
    if any(digest(Path(p))!=h for p,h in input_hashes.items()):
        raise ValueError('Source changed while scoring')
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps([r for r in summaries if r['field']=='all_fields_micro'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('training-review','validation-review','validation-config','validation-summary',
                 'training-manifest','validation-manifest','easyocr-run','trocr-run','paddleocr-run','output'):
        p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
