"""Build a blind human-labelling batch of route-text crops for a route hold-out set.

Why: test route text has only 4 scorable crops, too few to compare engines.
Every v4 test/valid route crop is already labelled, so new crops come from
train photos whose route crop was never labelled (Codex 3-copy consensus
failed). Those route crops never entered fine-tuning (lines are built only
from labelled review IDs), but other fields from the same photos did.

One crop per source photo (the largest of its augmented copies), so photos
are not double-counted. The page shows pixels only: no AI or OCR proposal.

Usage: python3 scripts/build_route_holdout_batch.py [OUT_DIR]
"""
import csv
import hashlib
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_human_review_page import human_page  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
V4 = REPO / '.cache/ocr_datasets/v4-reviewed-01/train/front_eds_route'
LABELS = REPO / 'evaluation/ocr_dataset/labels.csv'
SRC = re.compile(r'\d+_(.+?)_(?:jpg|jpeg|png)\.rf\.')


def source(name):
    m = SRC.match(name)
    if not m:
        raise ValueError('Unparsed crop name: ' + name)
    return m.group(1)


def main(out):
    out = Path(out)
    labelled = {source(Path(r['crop']).name) for r in csv.DictReader(open(LABELS, encoding='utf-8'))
                if r['split'] == 'train' and r['field'] == 'route_text'}
    groups = {}
    for p in sorted(V4.glob('*.png')):
        groups.setdefault(source(p.name), []).append(p)
    rows, manifest = [], []
    for i, (src, paths) in enumerate(sorted(g for g in groups.items() if g[0] not in labelled), 1):
        best = max(paths, key=lambda p: (lambda s: s[0] * s[1])(Image.open(p).size))
        rel = Path('crops') / best.name
        (out / 'crops').mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, out / rel)
        sha = hashlib.sha256((out / rel).read_bytes()).hexdigest()
        rid = f'RH{i:04d}'
        rows.append(dict(review_id=rid, crop=rel.as_posix(), field='route_text',
                         input_set='annotation', crop_sha256=sha))
        manifest.append(dict(review_id=rid, crop=rel.as_posix(), crop_sha256=sha, source_name=src,
                             origin_split='train', augmented_copies=len(paths)))
    with (out / 'manifest.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(manifest)
    n = human_page(out, 'review', f'Route hold-out: type {len(rows)} route-text crops',
                   rows, 'Route-text crops from train photos never labelled before. Type exactly what is visible.')
    print(f'{n} crops from {len(groups)} train route photos ({len(labelled)} already labelled, skipped) -> {out}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else REPO / '.runtime/route-holdout-20261117')
