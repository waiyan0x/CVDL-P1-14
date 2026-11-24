"""Document the frozen benchmark and v2 candidate; never invent unrun scores."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / 'evaluation/ocr_scoring/normalised-v8-layoutv3'
AUDIT = ROOT / 'evaluation/ocr_training/synthetic-v2-audit-20261119'
OUTPUT = ROOT / 'evaluation/OCR_RESULTS_SYNTHETIC_V2.md'
MODELS = [('paddleocr', 'PaddleOCR'), ('trocr', 'TrOCR'), ('easyocr', 'EasyOCR')]
FIELDS = [('front_eds_num', 'number'), ('front_eds_destination', 'destination'),
          ('front_eds_route', 'route'), ('all', '**all fields**')]


def cells(path):
    result = {}
    for model in json.loads(path.read_text())['models']:
        for variant, v in model['variants'].items():
            for c in v['cells']:
                result[model['id'], variant, c['split'], c['input_set'], c['field']] = c
    return result


def main():
    if OUTPUT.exists():
        prior = json.loads((AUDIT/'results_manifest.json').read_text())
        if hashlib.sha256(OUTPUT.read_bytes()).hexdigest() != prior['report_sha256']:
            raise SystemExit('Refusing to overwrite an edited consolidated report')
    real, syn = cells(SNAP/'scores/report.json'), cells(SNAP/'syn/scores/report.json')
    hr, hs = cells(SNAP/'holdout/real/report.json'), cells(SNAP/'holdout/syn/report.json')
    audit = json.loads((AUDIT/'audit.json').read_text())
    review_status = ('100-crop human sample confirmed by user chat attestation; remaining crops not individually reviewed'
                     if audit['human_spotcheck_complete'] else '100-crop human sample pending')
    counts = audit['candidate_checks']['counts']
    assert audit['candidate_bundle']['training_run_completed'] is False
    lines = ['# OCR results — synthetic v2 consolidation', '',
             '**Status — 19 November 2026:** data preparation and existing benchmark consolidation only. '
             'The new 10,000-crop dataset has no returned trained checkpoints or OCR predictions. '
             'All new-v2 accuracy cells are **Pending training/evaluation**, not zero.', '',
             '**Selected matching model remains real-only fine-tuned PaddleOCR**, run '
             '`20261117-031848`: test CER 8.2%, WER 19.1%, exact 82.2%, n=45. '
             'No v2 model has been selected or passed to matching.', '',
             '## Data and version definitions', '',
             '| Version | Training data | Evidence/status |', '| --- | --- | --- |',
             '| pre | Original public weights | Existing saved inference |',
             '| fine | 366 real training lines; run 20261117-031848 | Existing saved inference |',
             '| syn1 | 366 real + 2,169 synthetic lines; run 20261118-084149 | Existing saved inference; older 2,000-crop generator |',
             f'| syn2 | {counts["real_train_pairs"]:,} real + {counts["synthetic_pairs"]:,} synthetic lines | New candidate; training/evaluation pending |', '',
             'Synthetic v2: 10,000 crops, all export-compatible, producing 10,196 lines; '
             '10,562 total training pairs, 96.5% synthetic. There are 4,000 number crops '
             '(60 distinct texts), 4,000 destination crops (268), and 2,000 route crops (8). '
             'These are rendered training labels, not human-verified OCR evaluation truth.', '',
             '**Observed checks:** ZIP CRC, every crop hash, held-out text exclusion, '
             'all candidate payload hashes, unchanged real training lines, and unchanged '
             'validation inputs relative to the real-v3 base passed. Review status: ' + review_status +
             '. Original v2 producer source remains outstanding. Audit: '
             '[audit.json](ocr_training/synthetic-v2-audit-20261119/audit.json).', '',
             '## Benchmark protocol', '',
             'Observed references: [reviewed text-label dataset](ocr_dataset/reviewed-20261119/README.md). '
             'Validation has 79 eligible annotation + 51 detector crops; test has 45 eligible '
             'annotation crops out of 118 reviewed. Train diagnostics use 384 eligible rows '
             'of 387, with the recorded human spot-check overrides. Partial/illegible and '
             'other excluded rows remain in the label dataset with reasons.', '',
             'The same real crops, references and frozen geometry apply to all columns. '
             'Validation uses v4-lines-v3, so its older-version numbers are re-scored from '
             'v3 runs rather than copied from the historical v1/v2 report. Test and hold-out '
             'geometry are unchanged. Prior checkpoints retain their historical training-time '
             'validation geometry; v2 training will use v3. Report this protocol difference.', '',
             'Normalisation: NFC, casefold, NFC, whitespace collapse; punctuation retained. '
             'CER/WER are micro edit rates (lower is better); exact match is per crop '
             '(higher is better). Failed/missing predictions count as empty. All rates below '
             'are percentages. Raw OCR is retained separately; bus_information.csv is a '
             'matching reference, not the text answer key. No CSV-corrected accuracy is claimed.', '']

    def table(title, split, population, r=real, s=syn, note=''):
        lines.extend([f'## {title}', '', note, ''] if note else [f'## {title}', ''])
        lines.extend(['| Model | Field | n | '+' | '.join(f'{metric} {v}' for metric in ['CER','WER','Exact'] for v in ['pre','fine','syn1','syn2'])+' |',
                      '| --- | --- | ---: |'+' ---: |'*12])
        for model, name in MODELS:
            for field, label in FIELDS:
                key=(model,'baseline',split,population,field)
                c=r.get(key)
                if not c or c['status']=='No samples':
                    continue
                versions=[c,r[model,'finetuned',split,population,field],s[model,'finetuned',split,population,field]]
                assert all(x['eligible']==c['eligible'] and x['status']=='Scored' for x in versions)
                values=[]
                for metric in ['cer','wer','exact_match']:
                    values += [f'{100*x[metric]:.1f}' for x in versions]+['Pending']
                lines.append(f'| {name} | {label} | {c["eligible"]} | '+' | '.join(values)+' |')
        lines.append('')

    table('Table 1a: test annotation crops', 'test','annotation',note='Route has only four eligible test crops; interpret separately with caution. syn2 has not been run.')
    table('Table 1b: validation annotation crops','valid','annotation',note='Validation also selects training epochs; fine-tuned validation results are optimistic.')
    table('Table 1c: train annotation crops — diagnostic only','train','annotation',note='AI-assisted references and training examples: not a held-out accuracy estimate.')
    table('Table 2: detector crops — validation only','valid','prediction',note='No test detector-crop benchmark was requested. This does not measure missed detections or whole-screen detection.')
    table('Table 4a: route hold-out, full crops — supplementary','train','annotation',hr,hs,
          'One human reviewer, 27 full crops from train photos. Their route text was withheld, but other fields from the photos may have been trained on; this is not unseen-scene independence.')
    lines += ['## Table 4b: route hold-out, partial crops — diagnostic only','',
              'Only readable text is scored; [UNK] spans are wildcards. These are not ordinary full-text OCR scores. '
              'Ranges are seeded crop-bootstrap 95% intervals.', '',
              '| Model | Version | n | Readable CER | 95% range | All readable correct |',
              '| --- | --- | ---: | ---: | --- | ---: |']
    for r in csv.DictReader((SNAP/'partial/summary.csv').open()):
        lines.append(f'| {r["model"]} | {r["version"]} | {r["crops"]} | {r["known_text_cer"]} | {r["ci_low"]}–{r["ci_high"]} | {r["all_readable_correct_pct"]} |')
    for _,name in MODELS:lines.append(f'| {name} | syn2 | 49 planned | Pending | Pending | Pending |')
    lines += ['', '## Table 3: v2 checkpoint selection — step 5', '',
              '| Model | Run ID | Best epoch | Validation crop CER | Reload/runner check |',
              '| --- | --- | --- | --- | --- |']
    for _,name in MODELS:lines.append(f'| {name} | Pending | Pending | Pending | Pending |')
    lines += ['', '## Improvement and selection — step 7', '',
              'Planned v2 batch size is now 32 by user request on 20 November 2026, '
              'rather than historical 8. This configuration has not been tested on '
              'the T4 at full batch size; CPU smoke checks do not establish memory fit. '
              'There are 331 batches per epoch, at most 6,620 across 20 epochs. '
              'A changed batch size can alter optimisation and does not guarantee faster training.', '',
              'Maximum epochs remain 20. All three trainers now implement validation crop-CER '
              'early stopping with patience 3 and retain the best checkpoint. Use the updated '
              '`ocr_finetune_code-20261120-earlystop.zip` with the current notebook. '
              'Paddle early-stop/export integration is locally checked but not yet verified in Colab.', '',
              'Observed syn1 versus fine: EasyOCR test CER improves 21.6 → 19.5 and WER '
              '45.7 → 42.6, but exact falls 60.0 → 55.6. PaddleOCR regresses on all three '
              'test metrics (CER 8.2 → 9.8); TrOCR also regresses (CER 17.4 → 34.6). '
              'No v2 improvement can be measured until new checkpoints are trained and evaluated.', '',
              '**Project decision:** preserve the agreed replacement rule: a new model must '
              'beat every other fine-tuned version on at least two of test CER/WER/exact '
              'and have validation/route hold-out CER no worse than its own real-only version. '
              'TEST was already used for selection and is not an independent final estimate. '
              'Do not tune training settings or matching cutoffs on TEST.', '',
              'The full candidate changes synthetic ratio and optimiser-step budget as well '
              'as image rendering. Any gain is a combined experiment result, not proof '
              'that v2 rendering alone improved OCR. A matched-data/update-budget control '
              'is a proposed follow-up, not a completed run.', '',
              '## Steps 2–8 and handoff', '',
              '| Step | Current status |', '| --- | --- |',
              '| 2: text labels | Reviewed real references consolidated; synthetic automated checks pass; ' + review_status + ' |',
              '| 3: test set | Existing real test/hold-out labels and layouts preserved; no test files in candidate training bundle |',
              '| 4: pretrained baseline | Existing scores reproduced exactly; current v3 validation runs used |',
              '| 5: fine-tuning | Candidate data/code and new Colab notebook prepared; no Colab smoke check, training or reload yet |',
              '| 6: evaluation | New weights/predictions pending; use separate synv2 run directories and fixed real references |',
              '| 7: selection | Pending v2 results; existing real-only PaddleOCR remains selected |',
              '| 8: results | This document consolidates existing measured scores and explicitly pending v2 cells |', '',
              'Upload instructions, notebook, data/code ZIP hashes and review material: '
              '[v2 preparation audit](ocr_training/synthetic-v2-audit-20261119/README.md). '
              'The notebook is `colab/ocr_finetune/ocr_finetune_synthetic_v2.ipynb`. '
              'Return each best/ ZIP, config, epoch log, selection, RUN_ID and input receipt. '
              'The historical synthetic runners hard-code old run names; do not run them '
              'unchanged against v2 weights and overwrite/reuse old outputs.', '',
              'Current matching package: `.runtime/ocr-matching-final-20261119.zip`. '
              'Keep its weights and raw/normalised OCR until step 7 selects a replacement. '
              'Text labels remain separate from matching inputs. Display ownership still '
              'needs human confirmation before fields are combined. No end-to-end '
              'pipeline accuracy, latency, FPS or matched-output result is claimed.', '',
              '## Evidence and reproducibility', '',
              'Measured cells come from `ocr_scoring/normalised-v8-layoutv3/`: '
              '`scores/report.json`, `syn/scores/report.json`, both hold-out reports '
              'and `partial/summary.csv`. Dataset/candidate evidence is in '
              '`ocr_training/synthetic-v2-audit-20261119/`. Source hashes are recorded in '
              '`results_manifest.json` there. Regenerate into a new destination after '
              'new inference/scoring; do not relabel pending cells with estimates.', '']
    OUTPUT.write_text('\n'.join(lines))
    sources=[SNAP/'scores/report.json', SNAP/'syn/scores/report.json',
             SNAP/'holdout/real/report.json',SNAP/'holdout/syn/report.json',
             SNAP/'partial/summary.csv',AUDIT/'audit.json']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (AUDIT/'results_manifest.json').write_text(json.dumps({
        'v2_status':'not_trained_or_evaluated',
        'sources_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'report':str(OUTPUT.relative_to(ROOT)), 'report_sha256':sha(OUTPUT)},indent=2)+'\n')
    print(OUTPUT)


if __name__=='__main__':
    main()
