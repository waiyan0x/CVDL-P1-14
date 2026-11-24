"""PROVISIONAL validation-only matching inputs from one saved pretrained OCR run.

For the reference-matching teammate to build and tune code before the fine-tuned
model is selected. Same record format as the final Step 9 handoff. Labels are
written to a separate CSV keyed by review_id and never enter the JSONL.
Test data is not read.

candidate_display_id groups text crops that sit on the same EDS panel box in the
same photo: annotation crops use annotated panels, detector crops use detected
panels. A text box is assigned to the panel covering the largest share of its
area (at least 50%); otherwise it gets its own id and display_assignment=none.

Usage:
  python3 scripts/export_provisional_matching_inputs.py \
    --run evaluation/ocr_runs/paddleocr-pretrained-valid \
    --scoring evaluation/ocr_scoring/normalised-v4-valid-human-corrected \
    --output .runtime/ocr-matching-provisional-20261117
"""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.crop_scoring import normalise_text  # noqa: E402

FIELD = {'front_eds_num': 'bus_number', 'front_eds_destination': 'destination', 'front_eds_route': 'route_text'}
DETECTOR_MANIFEST = ROOT / '.runtime/ocr-task-files-20261116/metadata/validation_detector_manifest.json'
REFERENCE = ROOT / 'data/bus_information.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def covered(text_box, panel_box):
    x1, y1 = max(text_box[0], panel_box[0]), max(text_box[1], panel_box[1])
    x2, y2 = min(text_box[2], panel_box[2]), min(text_box[3], panel_box[3])
    area = (text_box[2] - text_box[0]) * (text_box[3] - text_box[1])
    return max(0, x2 - x1) * max(0, y2 - y1) / area if area > 0 else 0.0


def panel_ref(crop):
    return Path(crop).stem.rsplit('_', 1)[-1]  # a9 / p000


def main(a):
    if a.output.exists():
        raise SystemExit(f'{a.output} exists; refusing to overwrite')
    manifest = json.loads((a.scoring / 'manifest.json').read_text())
    rows = {r['review_id']: r for r in manifest['rows']}
    if any(r['split'] != 'valid' for r in rows.values()):
        raise SystemExit('validation only: scoring manifest contains non-valid rows')
    report = json.loads((a.run / 'report.json').read_text())
    preds = {p['review_id']: p for p in map(json.loads, (a.run / 'predictions.jsonl').read_text().splitlines())}
    if set(preds) != set(rows):
        raise SystemExit('run and scoring manifest cover different crops')

    panels = {}
    for im in json.loads(DETECTOR_MANIFEST.read_text())['images']:
        panels[(im['image'], 'annotation')] = [g for g in im['ground_truth'] if g['label'] == 'front_eds']
        panels[(im['image'], 'prediction')] = [p for p in im['predictions'] if p['label'] == 'front_eds']

    records, labels, assign = [], [], Counter()
    for rid in sorted(rows):
        r, p = rows[rid], preds[rid]
        if p['crop_sha256'] != r['crop_sha256']:
            raise SystemExit(f'{rid}: crop hash differs between run and manifest')
        box = json.loads(r['box_xyxy'])
        stem = Path(r['image']).stem
        best = max(panels.get((r['image'], r['crop_source']), []), key=lambda q: covered(box, q['box_xyxy']), default=None)
        if best is not None and covered(box, best['box_xyxy']) >= 0.5:
            display, how = f"{r['crop_source']}:{stem}:{panel_ref(best['crop'])}", 'panel'
        else:
            display, how = f"{r['crop_source']}:{stem}:solo-{rid}", 'none'
        assign[(r['crop_source'], how)] += 1
        raw = p.get('raw_text') if p['status'] == 'success' else None
        records.append(dict(
            record_id=f"{report['engine']}/pretrained/{rid}", review_id=rid, model=report['engine'],
            variant='pretrained', provisional=True, split='valid', input_set=r['crop_source'], field=FIELD[r['label']],
            source_image=r['image'], source_image_sha256=r['source_image_sha256'], crop=r['crop'],
            crop_sha256=r['crop_sha256'], box_xyxy=box, candidate_display_id=display, display_assignment=how,
            raw_ocr_text=raw, normalised_ocr_text=normalise_text(raw) if raw is not None else None,
            prediction_status=p['status'], ocr_confidence=p.get('ocr_confidence'),
            detector_confidence=float(r['detector_confidence']) if r.get('detector_confidence') else None))
        labels.append(dict(review_id=rid, split='valid', input_set=r['crop_source'], field=FIELD[r['label']],
                           text=r['transcription'], legibility=r['legibility'], field_status=r['field_status'],
                           scoring_eligible=r['scoring_eligible'], exclusion_reason=';'.join(r['scoring_blockers'])))

    a.output.mkdir(parents=True)
    (a.output / 'matching_inputs.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in records))
    with open(a.output / 'validation_labels.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, list(labels[0]), lineterminator='\n'); w.writeheader(); w.writerows(labels)
    (a.output / 'reference').mkdir()
    shutil.copyfile(REFERENCE, a.output / 'reference/bus_information.csv')
    displays = Counter(x['candidate_display_id'] for x in records)
    summary = dict(provisional=True, purpose='build/tune matching code on validation; NOT the final Step 9 handoff',
                   model=report['engine'], model_identity=report.get('model'), variant='pretrained',
                   records=len(records), statuses=dict(Counter(x['prediction_status'] for x in records)),
                   input_sets=dict(Counter(x['input_set'] for x in records)),
                   display_assignment={f'{k[0]}/{k[1]}': v for k, v in assign.items()},
                   displays=len(displays), multi_field_displays=sum(v > 1 for v in displays.values()),
                   whole_display_ocr='not included (front_eds panel OCR not run yet)', test_accessed=False,
                   sources=dict(run_predictions_sha256=sha(a.run / 'predictions.jsonl'),
                                run_report_sha256=sha(a.run / 'report.json'),
                                scoring_manifest_sha256=manifest['manifest_sha256'],
                                detector_manifest_sha256=sha(DETECTOR_MANIFEST), reference_sha256=sha(REFERENCE)))
    (a.output / 'handoff_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ('records', 'statuses', 'input_sets', 'display_assignment', 'displays',
                                              'multi_field_displays')}, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--scoring', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    main(ap.parse_args())
