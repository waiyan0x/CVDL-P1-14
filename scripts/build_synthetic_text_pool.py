#!/usr/bin/env python3
"""Allowed text list for prompting an image generator (synthetic EDS crops).

Candidates come from the round 2 generator's pool logic
(scripts/generate_synthetic_eds_crops.py: exact train-label strings plus
compositions of train-only words). Each candidate is then dropped if any line or
the whole label matches held-out evaluation text under the stricter key in
scripts/synthetic_heldout.py, or if any line exceeds PaddleOCR's CTC limit.
Only allowed text is written; held-out strings are never written to the output.

Outputs (OUT_DIR, default .runtime/synthetic-text-pool-<date>):
  allowed_text.csv     field, text (real newlines), text_escaped (\\n), origin, lines, max_ctc
  allowed_<field>.txt  one escaped string per line, for pasting into prompts
  pool_manifest.json   counts, seed, input hashes, drop reasons

Usage: .venv/bin/python scripts/build_synthetic_text_pool.py [--out DIR] [--seed 0] [--no-compose]
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_synthetic_eds_crops as gen  # noqa: E402
from synthetic_heldout import FIELDS, PADDLE_CTC_STEPS, ROOT, ctc_need, held_keys, leaks  # noqa: E402


def escape(text):
    return text.replace('\n', '\\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=ROOT / f'.runtime/synthetic-text-pool-{dt.date.today():%Y%m%d}')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--no-compose', action='store_true')
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f'{a.out} exists; choose a new --out')

    pools, _ = gen.load_pools(not a.no_compose, random.Random(a.seed))
    keys, provenance = held_keys()
    rows, dropped = [], {f: {'held_out_text': 0, 'over_ctc_limit': 0, 'duplicate_key': 0} for f in FIELDS}
    for field in FIELDS:
        seen = set()
        for text, origin in pools[field]:
            text = text.strip()
            if leaks(text, keys):
                dropped[field]['held_out_text'] += 1
                continue
            max_ctc = max(ctc_need(line) for line in text.split('\n'))
            if max_ctc > PADDLE_CTC_STEPS:
                dropped[field]['over_ctc_limit'] += 1
                continue
            k = text.casefold()
            if k in seen:
                dropped[field]['duplicate_key'] += 1
                continue
            seen.add(k)
            rows.append(dict(field=field, text=text, text_escaped=escape(text), origin=origin,
                             lines=text.count('\n') + 1, max_ctc=max_ctc))

    a.out.mkdir(parents=True)
    with (a.out / 'allowed_text.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    for field in FIELDS:
        (a.out / f'allowed_{field}.txt').write_text(
            ''.join(r['text_escaped'] + '\n' for r in rows if r['field'] == field), encoding='utf-8')
    counts = {f: dict(allowed=sum(r['field'] == f for r in rows),
                      label_exact=sum(r['field'] == f and r['origin'] == 'label_exact' for r in rows),
                      composed=sum(r['field'] == f and r['origin'] != 'label_exact' for r in rows),
                      dropped=dropped[f]) for f in FIELDS}
    manifest = dict(script='scripts/build_synthetic_text_pool.py', created=dt.datetime.now().isoformat(timespec='seconds'),
                    seed=a.seed, compose=not a.no_compose, held_out_keys=len(keys), held_out_sources=provenance,
                    generator_labels_sha256=hashlib.sha256(gen.LABELS.read_bytes()).hexdigest(),
                    ctc_limit=PADDLE_CTC_STEPS, counts=counts,
                    note='Text only. Labels must still be checked against the generated image.')
    (a.out / 'pool_manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(dict(out=str(a.out), counts=counts), indent=1))


if __name__ == '__main__':
    main()
