"""Build matching_inputs.jsonl for the 5k-split fine-tuned PaddleOCR model.

Reuses the round 1 record layout (crops, display-ownership geometry) from
.runtime/ocr-matching-final-20261119 and replaces only the OCR fields with the
5k model's saved runs. Refuses to overwrite existing outputs. No matching.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.crop_scoring import normalise_text

BASE = ROOT / '.runtime/ocr-matching-final-20261119'
RUNS = {'valid': ROOT / '.cache/ocr_runs/paddleocr-ocr5k-valid-layoutv3',
        'test': ROOT / '.cache/ocr_runs/paddleocr-ocr5k-test'}
VARIANT = 'finetuned_5k'
TRAINING_RUN = 'ocr5k-split-b32-e20-20261120-084105'
OCR_FIELDS = ('raw_ocr_text', 'normalised_ocr_text', 'prediction_status', 'error', 'ocr_confidence')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', type=Path, required=True, help='Output package folder (must contain inference/panel_predictions.jsonl)')
    ap.add_argument('--weights', type=Path, required=True)
    a = ap.parse_args()
    out = a.package
    for name in ('matching_inputs.jsonl', 'matching_outputs.template.csv', 'models.lock.json'):
        if (out / name).exists():
            raise FileExistsError(out / name)

    new = {}
    for split, run in RUNS.items():
        report = json.loads((run / 'report.json').read_text())
        if report['status'] != 'complete' or report['model_sha256_before'] != report['model_sha256_after']:
            raise ValueError(f'Run not complete or weights changed: {run}')
        for p in load_jsonl(run / 'predictions.jsonl'):
            new[p['review_id']] = dict(raw=p['raw_text'], status=p['status'], error=p.get('error'),
                                       conf=p.get('ocr_confidence'), crop_sha256=p['crop_sha256'])
    for p in load_jsonl(out / 'inference/panel_predictions.jsonl'):
        if p['review_id'] in new:
            raise ValueError('Duplicate review_id across runs: ' + p['review_id'])
        new[p['review_id']] = dict(raw=p['raw_text'], status=p['status'], error=p.get('error'),
                                   conf=p.get('ocr_confidence'), crop_sha256=p['crop_sha256'])

    base = load_jsonl(BASE / 'matching_inputs.jsonl')
    if {r['review_id'] for r in base} != set(new):
        raise ValueError('5k runs do not cover exactly the round 1 matching crops')
    records = []
    for r in base:
        n = new[r['review_id']]
        if n['crop_sha256'] != r['crop_sha256']:
            raise ValueError('Crop pixels differ for ' + r['review_id'])
        rec = dict(r)
        rec.update(record_id=f"paddleocr/{VARIANT}/{r['review_id']}", variant=VARIANT,
                   raw_ocr_text=n['raw'], normalised_ocr_text=normalise_text(n['raw']),
                   prediction_status=n['status'], error=n['error'], ocr_confidence=n['conf'])
        records.append(rec)
    (out / 'matching_inputs.jsonl').write_text(
        ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records))

    with (out / 'matching_outputs.template.csv').open('w', newline='') as f:
        columns = next(csv.reader((BASE / 'matching_outputs.template.csv').open()))
        w = csv.DictWriter(f, columns)
        w.writeheader()
        for r in records:
            w.writerow(dict(record_id=r['record_id'], matching_status='pending'))

    weight_files = ('inference.json', 'inference.pdiparams', 'inference.yml', 'provenance.json')
    lock = dict(model='PaddleOCR en_PP-OCRv5_mobile_rec', variant=VARIANT, training_run=TRAINING_RUN,
                training_dataset_note='5k split: 4,000 training line images (297 original real, 3,703 rendered)',
                selected_epoch=9, validation_crop_CER_5k_split=0.009662828947368422,
                records=len(records), base_layout_from='ocr-matching-final-20261119 (round 1 records; OCR fields replaced)',
                model_files_sha256={n: sha(a.weights / n) for n in weight_files},
                source_runs_sha256={str(run.relative_to(ROOT)): dict(predictions=sha(run / 'predictions.jsonl'),
                                                                    report=sha(run / 'report.json'))
                                    for run in RUNS.values()},
                files_sha256={n: sha(out / n) for n in ('matching_inputs.jsonl', 'matching_outputs.template.csv',
                                                        'inference/panel_predictions.jsonl')},
                test_benchmark_passed=False,
                display_ownership='geometry proposals; human review pending',
                replaces_round1_delivery=False)
    (out / 'models.lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    print('records', len(records))


if __name__ == '__main__':
    main()
