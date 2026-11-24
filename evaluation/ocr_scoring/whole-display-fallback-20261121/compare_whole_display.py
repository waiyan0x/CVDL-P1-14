"""Compare fine-tuned and pretrained PaddleOCR on whole-display (front_eds) crops.

There are no whole-display text labels. A display is scored only when the same
candidate display has full-legibility number and destination labels that the app
matcher can match; the reading is correct when the app's whole-display split plus
matcher returns the same service and endpoint. Display grouping is an unreviewed
geometry proposal. Uses the app's own worker, split and matcher code.

Usage (from the repository root, with the matching package unzipped in .runtime):
    .venv/bin/python -I evaluation/ocr_scoring/whole-display-fallback-20261121/compare_whole_display.py OUT_DIR
"""
import base64
import collections
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.matching import RouteMatcher  # noqa: E402
from backend.app.services.ocr.paddleocr import WORKER, verify_model  # noqa: E402

PACKAGE = ROOT / '.runtime/ocr-matching-final-20261119'


def read_all(python, model_dir, panels):
    process = subprocess.Popen([str(python), '-I', str(WORKER), str(model_dir)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if not json.loads(process.stdout.readline()).get('ready'):
        raise RuntimeError(f'Worker failed for {model_dir}')
    out = {}
    for panel in panels:
        png = (PACKAGE / panel['crop_path']).read_bytes()
        process.stdin.write(json.dumps({'png_b64': base64.b64encode(png).decode()}) + '\n')
        process.stdin.flush()
        out[panel['review_id']] = json.loads(process.stdout.readline())
    process.stdin.close()
    process.wait()
    return out


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=False)
    settings = Settings(root=ROOT)
    models = {'finetuned': settings.paddle_model_dir, 'pretrained': settings.paddle_pretrained_dir}
    verify_model(models['finetuned'], fine_tuned=True)
    verify_model(models['pretrained'], fine_tuned=False)
    matcher = RouteMatcher(ROOT / 'data/bus_information.csv')
    panels = json.loads((PACKAGE / 'inference/panel_inventory.json').read_text())
    records = [json.loads(line) for line in (PACKAGE / 'matching_inputs.jsonl').open()]
    labels = {r['review_id']: r for name in ('validation_labels.csv', 'test_labels.csv')
              for r in csv.DictReader((PACKAGE / name).open())}
    truth_fields = collections.defaultdict(dict)
    for record in records:
        label = labels.get(record['review_id'])
        if (record['field'] in ('bus_number', 'destination') and record.get('candidate_display_id') and label
                and label['legibility'] == 'full' and label['field_status'] == 'present'):
            truth_fields[record['candidate_display_id']][record['field']] = label['text']

    rows, summary = [], collections.defaultdict(collections.Counter)
    for name, model_dir in models.items():
        readings = read_all(settings.paddle_python_path, model_dir, panels)
        for panel in panels:
            reading = readings[panel['review_id']]
            service, rest = matcher.split_display(reading['text'])
            truth = truth_fields.get(panel.get('candidate_display_id'), {})
            counts = summary[(name, panel['split'])]
            counts['panels'] += 1
            counts['no_text'] += not reading['text']
            number_ok = expected = None
            if 'bus_number' in truth:
                counts['number_labelled'] += 1
                number_ok = service == re.sub(r'\s+', '', truth['bus_number'].upper())
                counts['number_correct'] += number_ok
            if {'bus_number', 'destination'} <= truth.keys():
                expected = matcher.match(truth['bus_number'], truth['destination'])
            display_ok = None
            if expected and expected['status'] == 'matched':
                counts['matchable_displays'] += 1
                got = matcher.match(service, rest)
                display_ok = got['status'] == 'matched' and (got['service'], got['endpoint']) == (expected['service'], expected['endpoint'])
                counts['matched_correct'] += display_ok
                counts['matched_wrong'] += got['status'] == 'matched' and not display_ok
            rows.append({'model': name, 'review_id': panel['review_id'], 'split': panel['split'],
                         'crop_set': panel['crop_set'], 'raw_text': reading['text'], 'confidence': reading['confidence'],
                         'error': reading['error'], 'split_service': service, 'split_rest': rest,
                         'number_correct': number_ok, 'display_matched_correct': display_ok})
    with (out_dir / 'readings.jsonl').open('x') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    table = [{'model': model, 'split': split, **counts} for (model, split), counts in sorted(summary.items())]
    (out_dir / 'summary.json').write_text(json.dumps(table, indent=2) + '\n')
    for row in table:
        print(row)


if __name__ == '__main__':
    main()
