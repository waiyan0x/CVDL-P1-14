"""Diagnostic score for partial-legibility crops: readable text only.

Each [UNK] in the reference is a wildcard that matches any hypothesis text
(including none) at zero cost; whitespace next to [UNK] is folded into the
wildcard. Everything else is ordinary character edit distance under the
project's normalised scoring (casefold, whitespace collapsed).

  known-text CER = wildcard edit errors / readable reference characters
  all-readable-correct = wildcard edit distance is 0

This is NOT the official metric: official scoring excludes partial crops.
Usage: python3 scripts/score_partial_route.py SOURCE_CSV RUNS_DIR SUFFIX OUT_DIR
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.crop_scoring import normalise_text  # noqa: E402

WILD = None
MODELS = (('easyocr', 'EasyOCR'), ('trocr', 'TrOCR'), ('paddleocr', 'PaddleOCR'))
VARIANTS = (('pretrained', 'pretrained'), ('finetuned', 'fine-tuned'))


def pattern(reference):
    parts = re.split(r'\s*\[UNK\]\s*', reference)
    out = []
    for i, part in enumerate(parts):
        if i:
            out.append(WILD)
        out.extend(normalise_text(part))
    return out


def wildcard_distance(pat, hyp):
    prev = list(range(len(hyp) + 1))
    for token in pat:
        cur = [prev[0] + (token is not WILD)]
        for j, ch in enumerate(hyp, 1):
            if token is WILD:
                cur.append(min(prev[j], cur[j - 1]))
            else:
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (token != ch)))
        prev = cur
    return prev[-1]


def main(source, runs, suffix, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(open(source, encoding='utf-8')) if r['legibility'] == 'partial']
    refs = {r['review_id']: pattern(r['transcription']) for r in rows}
    ids = sorted(refs)
    per, records = {}, []
    for model, _ in MODELS:
        for variant, _ in VARIANTS:
            key = f'{model}-{variant}'
            preds = {}
            for line in open(Path(runs) / f'{model}-{variant}-{suffix}' / 'predictions.jsonl', encoding='utf-8'):
                p = json.loads(line)
                preds[p['review_id']] = p
            per[key] = {}
            for rid in ids:
                p = preds.get(rid)
                ok = p is not None and p['status'] == 'success'
                hyp = normalise_text(p['raw_text']) if ok else ''
                known = sum(t is not WILD for t in refs[rid])
                dist = wildcard_distance(refs[rid], hyp)
                per[key][rid] = (dist, known)
                records.append(dict(model=model, variant=variant, review_id=rid,
                                    reference=next(r['transcription'] for r in rows if r['review_id'] == rid),
                                    raw_ocr_text=p['raw_text'] if p else None,
                                    prediction_status=p['status'] if p else 'missing',
                                    readable_chars=known, errors=dist))
    random.seed(0)
    boots = [[random.choice(ids) for _ in ids] for _ in range(5000)]

    def cer(key, sample):
        return 100 * sum(per[key][i][0] for i in sample) / sum(per[key][i][1] for i in sample)

    def ci(values):
        values = sorted(values)
        return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]

    summary = []
    for model, mname in MODELS:
        for variant, vname in VARIANTS:
            key = f'{model}-{variant}'
            lo, hi = ci([cer(key, s) for s in boots])
            summary.append(dict(model=mname, version=vname, crops=len(ids),
                                readable_chars=sum(per[key][i][1] for i in ids),
                                known_text_cer=round(cer(key, ids), 1), ci_low=round(lo, 1), ci_high=round(hi, 1),
                                all_readable_correct_pct=round(100 * sum(per[key][i][0] == 0 for i in ids) / len(ids), 1),
                                failed=sum(r['prediction_status'] != 'success' for r in records
                                           if r['model'] == model and r['variant'] == variant)))
    pairs = [('paddleocr-finetuned', 'easyocr-finetuned'), ('paddleocr-finetuned', 'trocr-finetuned'),
             ('paddleocr-pretrained', 'easyocr-pretrained'), ('paddleocr-pretrained', 'trocr-pretrained'),
             ('easyocr-finetuned', 'easyocr-pretrained'), ('trocr-finetuned', 'trocr-pretrained'),
             ('paddleocr-finetuned', 'paddleocr-pretrained')]
    diffs = []
    for a, b in pairs:
        lo, hi = ci([cer(a, s) - cer(b, s) for s in boots])
        diffs.append(dict(comparison=f'{a} − {b}', difference=round(cer(a, ids) - cer(b, ids), 1),
                          ci_low=round(lo, 1), ci_high=round(hi, 1)))
    for name, data in (('summary.csv', summary), ('paired_differences.csv', diffs), ('text_records.csv', records)):
        with (out / name).open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
            w.writeheader()
            w.writerows(data)
    print(json.dumps(dict(summary=summary, paired=diffs), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:5])
