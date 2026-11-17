"""Render synthetic dot-matrix EDS text crops plus a labels.csv ground truth.

Purpose: fine-tuning data only. Every row is split=train, input_set=synthetic,
scoring_eligible=False, so no scorer can count it.

Text pool (no outside road list):
  * exact strings from train labels (full legibility, no [UNK]);
  * optional compositions from train-only words (``--no-compose`` to disable).
Any string whose normalised form appears in valid, test or the route hold-out
set is dropped, so synthetic text never overlaps an evaluation reference.

Rendering imitates real crops: a TTF glyph mask is sampled onto an LED grid,
drawn as lit/unlit dots with glow, then tilted, blurred, noised, resized to a
height drawn from the real crop sizes of that field, and JPEG round-tripped.

The crop<->text mapping is the labels.csv row: review_id, crop path and
crop_sha256 (verified after writing). manifest.json records seed, pools and
per-crop render parameters, so the set is reproducible.

Usage: python3 scripts/generate_synthetic_eds_crops.py [--out DIR] [--count N] [--seed S] [--no-compose]
"""
import argparse
import csv
import hashlib
import io
import json
import random
import re
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
LABELS = REPO / 'evaluation/ocr_dataset/labels.csv'
HOLDOUT = REPO / 'evaluation/ocr_review/route-holdout-20261117/route_holdout.source.csv'
REAL_CROPS = REPO / '.runtime/ocr-text-dataset-20261116'
FONTS = ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
         '/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf',
         '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf',
         '/System/Library/Fonts/Supplemental/Arial.ttf']
COLOURS = {'amber': (255, 150, 20), 'orange': (255, 105, 25), 'yellow': (255, 215, 60), 'white': (238, 238, 225)}
FIELDS = {'route_text': 0.45, 'destination': 0.30, 'bus_number': 0.25}
SUFFIXES = ('AVE', 'RD', 'ST', 'DR', 'CRES', 'CENTRAL')
COLUMNS = ['review_id', 'split', 'input_set', 'field', 'crop', 'crop_sha256', 'text', 'legibility', 'field_status',
           'label_source', 'human_check_status', 'scoring_eligible', 'exclusion_reason', 'source_name', 'note']


def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def usable(text):
    return text.strip() and '[UNK]' not in text


def load_pools(compose, rng):
    rows = list(csv.DictReader(open(LABELS, encoding='utf-8')))
    held = {norm(r['text']) for r in rows if r['split'] in ('valid', 'test') and usable(r['text'])}
    held |= {norm(r['transcription']) for r in csv.DictReader(open(HOLDOUT, encoding='utf-8'))
             if usable(r['transcription'])}
    exact = {f: sorted({r['text'] for r in rows if r['split'] == 'train' and r['field'] == f
                        and r['field_status'] == 'present' and usable(r['text'])}) for f in FIELDS}
    pools = {f: [(t, 'label_exact') for t in v if norm(t) not in held] for f, v in exact.items()}
    if compose:
        names, numbers = set(), set()
        for f in ('route_text', 'destination'):
            for text in exact[f]:
                for line in re.split(r'\n| - |-|/', text):
                    words = [w for w in line.replace('>', ' ').replace(',', ' ').split()
                             if w.upper() not in SUFFIXES + ('INT', 'TER', 'MRT', 'LRT', 'VIA', '(LOOP)', 'DIRECT')
                             and not re.fullmatch(r'\d+', w)]
                    if words and all(w.isupper() for w in words):
                        names.add(' '.join(words))
        names = sorted(names)
        suffix_letters = sorted({m for t in exact['bus_number'] for m in re.findall(r'[A-Za-z]$', t)})
        made = {f: set() for f in FIELDS}
        for _ in range(4000):
            a, b = rng.choice(names), rng.choice(names)
            s, n, m = rng.choice(SUFFIXES), rng.randint(1, 99), rng.randint(1, 99)
            made['route_text'].add(rng.choice([f'{a} {s}', f'{a} {s} {n}', f'{a} {s} {n}, {m}',
                                               f'{a} INT via\n{b} {s}', f'{a} {s} {n}\n{b} {s}']))
            made['destination'].add(rng.choice([f'{a} INT', f'{a} TER', f'> {a} INT', f'{a} MRT', f'{a} via',
                                                f'{a}\nINT / MRT']))
            num = str(rng.randint(2, 999))
            made['bus_number'].add(num + (rng.choice(suffix_letters) if suffix_letters and rng.random() < 0.2 else ''))
        have = {f: {norm(t) for t, _ in pools[f]} for f in FIELDS}
        for f in FIELDS:
            pools[f] += [(t, 'composed_train_words') for t in sorted(made[f])
                         if norm(t) not in held and norm(t) not in have[f]]
    return pools, len(held)


def real_heights():
    rows = list(csv.DictReader(open(LABELS, encoding='utf-8')))
    heights = {f: [] for f in FIELDS}
    for r in rows:
        path = REAL_CROPS / r['crop']
        if r['field'] in heights and path.is_file():
            heights[r['field']].append(Image.open(path).size[1])
    if not all(heights.values()):
        raise FileNotFoundError('Real crops missing: rebuild .runtime/ocr-text-dataset-20261116 first')
    return heights


def glyph_grid(text, font_path, rows_per_line):
    """Binary LED grid for each line, stacked with a one-row gap."""
    font = ImageFont.truetype(font_path, rows_per_line * 4)
    grids = []
    for line in text.split('\n'):
        box = font.getbbox(line or ' ')
        im = Image.new('L', (box[2] - box[0] + 8, box[3] - box[1] + 8))
        ImageDraw.Draw(im).text((4 - box[0], 4 - box[1]), line, fill=255, font=font)
        h = rows_per_line
        w = max(1, round(im.width * h / im.height))
        grids.append(np.asarray(im.resize((w, h), Image.BOX)) > 100)
    width = max(g.shape[1] for g in grids)
    out = []
    for i, g in enumerate(grids):
        if i:
            out.append(np.zeros((1, width), bool))
        pad = (width - g.shape[1]) // 2
        out.append(np.pad(g, ((0, 0), (pad, width - g.shape[1] - pad))))
    return np.vstack(out)


def render(text, field, rng, heights):
    p = dict(font=Path(rng.choice(FONTS)).name, rows=rng.randint(7, 12), pitch=rng.randint(4, 7),
             colour=rng.choices(list(COLOURS), weights=[4, 3, 2, 2])[0], dot=round(rng.uniform(0.32, 0.46), 2),
             unlit=round(rng.uniform(0, 0.12), 2), margin=rng.randint(0, 3), glow=round(rng.uniform(0, 1.6), 2),
             tilt=round(rng.uniform(-0.12, 0.12), 3), rotate=round(rng.uniform(-3, 3), 2),
             blur=round(rng.uniform(0, 1.4), 2), noise=round(rng.uniform(0, 14), 1), jpeg=rng.randint(30, 92),
             brightness=round(rng.uniform(0.55, 1.1), 2))
    grid = glyph_grid(text, next(f for f in FONTS if Path(f).name == p['font']), p['rows'])
    grid = np.pad(grid, p['margin'])
    pitch, colour = p['pitch'], np.array(COLOURS[p['colour']])
    bg = tuple(int(v) for v in rng.choice([(12, 12, 14), (25, 22, 20), (8, 10, 18), (35, 33, 30)]))
    im = Image.new('RGB', (grid.shape[1] * pitch, grid.shape[0] * pitch), bg)
    draw = ImageDraw.Draw(im)
    r = pitch * p['dot']
    for y, x in np.ndindex(grid.shape):
        cx, cy = x * pitch + pitch / 2, y * pitch + pitch / 2
        lit = grid[y, x]
        if lit or p['unlit']:
            c = colour * (p['brightness'] if lit else p['unlit'])
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(min(255, v)) for v in c))
    if p['glow']:
        glow = im.filter(ImageFilter.GaussianBlur(pitch * p['glow']))
        im = Image.fromarray(np.clip(np.asarray(im, float) + 0.6 * np.asarray(glow, float), 0, 255).astype(np.uint8))
    w, h = im.size
    shift = p['tilt'] * h
    im = im.transform((w + int(abs(shift)), h), Image.AFFINE, (1, p['tilt'], -max(0, shift) if shift > 0 else 0, 0, 1, 0),
                      resample=Image.BILINEAR, fillcolor=bg)
    im = im.rotate(p['rotate'], resample=Image.BILINEAR, expand=True, fillcolor=bg)
    target = rng.choice(heights[field])
    lines = text.count('\n') + 1
    target = max(14 * lines, min(target, im.height))  # keep every line legible: label says full
    im = im.resize((max(8, round(im.width * target / im.height)), target), Image.LANCZOS)
    if p['blur']:
        im = im.filter(ImageFilter.GaussianBlur(p['blur'] * target / 40))
    arr = np.asarray(im, float) + np.random.default_rng(rng.randint(0, 2**31)).normal(0, p['noise'], (im.height, im.width, 3))
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=p['jpeg'])
    p['size'] = list(im.size)
    return Image.open(io.BytesIO(buf.getvalue())).convert('RGB'), p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', type=Path, default=REPO / '.runtime/synthetic-eds-20261117')
    ap.add_argument('--count', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--no-compose', action='store_true')
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(f'{args.out} exists; choose a new --out')
    rng = random.Random(args.seed)
    pools, held_count = load_pools(not args.no_compose, rng)
    heights = real_heights()
    plan = [f for f, share in FIELDS.items() for _ in range(round(args.count * share))][:args.count]
    rows, params = [], []
    for i, field in enumerate(plan, 1):
        # 30% exact label strings (when any remain), 70% composed, so the few exact strings recur without dominating.
        exact = [x for x in pools[field] if x[1] == 'label_exact']
        composed = [x for x in pools[field] if x[1] != 'label_exact']
        text, origin = rng.choice(exact if exact and (not composed or rng.random() < 0.3) else composed)
        im, p = render(text, field, rng, heights)
        rid = f'SYN{i:05d}'
        rel = Path('crops') / field / f'{rid}.png'
        (args.out / rel.parent).mkdir(parents=True, exist_ok=True)
        im.save(args.out / rel)
        sha = hashlib.sha256((args.out / rel).read_bytes()).hexdigest()
        rows.append(dict(review_id=rid, split='train', input_set='synthetic', field=field, crop=rel.as_posix(),
                         crop_sha256=sha, text=text, legibility='full', field_status='present',
                         label_source='synthetic_render', human_check_status='not_applicable',
                         scoring_eligible=False, exclusion_reason='synthetic_training_only', source_name=origin,
                         note=''))
        params.append(dict(review_id=rid, **p))
    with (args.out / 'labels.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    for r in rows:  # verify the crop<->label mapping
        if hashlib.sha256((args.out / r['crop']).read_bytes()).hexdigest() != r['crop_sha256']:
            raise ValueError('Hash mismatch ' + r['review_id'])
    summary = {f: dict(crops=sum(r['field'] == f for r in rows),
                       pool_exact=sum(o == 'label_exact' for _, o in pools[f]),
                       pool_composed=sum(o != 'label_exact' for _, o in pools[f]),
                       unique_texts_used=len({r['text'] for r in rows if r['field'] == f})) for f in FIELDS}
    manifest = dict(generator='scripts/generate_synthetic_eds_crops.py', seed=args.seed, count=len(rows),
                    compose=not args.no_compose, excluded_eval_strings=held_count,
                    labels_sha256=hashlib.sha256(LABELS.read_bytes()).hexdigest(),
                    holdout_sha256=hashlib.sha256(HOLDOUT.read_bytes()).hexdigest(),
                    summary=summary, pools={f: v for f, v in pools.items()}, render_params=params)
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
