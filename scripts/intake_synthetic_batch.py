#!/usr/bin/env python3
"""Check a batch of externally generated EDS crops before it is used for training.

Input: BATCH_DIR with images and labels.csv (columns: file, field, text,
generator, prompt_id). field is bus_number, destination or route_text. text is
exactly what the display shows; a two-character \\n in the CSV means a line break.
Whole-display (front_eds) images are rejected: training uses one field's lines.

Rejections (reason in rejected.csv):
  missing_file, unreadable_image, too_small, unknown_field, empty_text,
  unknown_text_marker, tsv_unsafe_text, held_out_text, over_ctc_limit,
  duplicate_file, near_duplicate (same text, near-identical image),
  line_count_mismatch (automatic segmentation finds a different number of lines
  than the label has; add_synthetic_to_bundle.py would skip it anyway)
Warnings (kept, listed in accepted.csv note): new_characters, exif_rotation,
  large_image, similar_image_different_text, lines_joined.

Output OUT_DIR (default BATCH_DIR/intake), a synthetic set that
scripts/add_synthetic_to_bundle.py --synthetic OUT_DIR can consume:
  labels.csv, crops/<field>/<review_id>.<ext>   accepted crops (bytes unchanged)
  rejected.csv                                   every rejected row and its reasons
  spotcheck.csv, contact_sheet_NN.png            seeded random sample for human review
  intake_manifest.json                           counts, hashes, held-out sources

Labels are NOT verified against the image by this script. A human must fill in
spotcheck.csv (verdict: correct / wrong / unreadable) before the batch is used.
No OCR model is run, so no crop is removed for being hard to read.

Usage: .venv/bin/python scripts/intake_synthetic_batch.py BATCH_DIR --batch-id B01
         [--out DIR] [--against SET_DIR ...] [--sample 60] [--seed 0]
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import random
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synthetic_heldout import FIELDS, PADDLE_CTC_STEPS, ROOT, ctc_need, held_keys, key, leaks  # noqa: E402
from backend.app.evaluation.ocr_crop_baseline import segment_lines  # noqa: E402
from export_ocr_finetune_bundle import pairing  # noqa: E402

COLUMNS = ['review_id', 'split', 'input_set', 'field', 'crop', 'crop_sha256', 'text', 'legibility', 'field_status',
           'label_source', 'human_check_status', 'scoring_eligible', 'exclusion_reason', 'source_name', 'note']
REAL_LABELS = ROOT / 'evaluation/ocr_training/train_labels_final.csv'
MIN_SIDE, LARGE_SIDE, NEAR_DUP_BITS = 10, 1000, 3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dhash(im):
    g = np.asarray(im.convert('L').resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int(''.join('1' if b else '0' for b in bits), 2)


def known_sets(dirs):
    """Hashes of previously accepted synthetic sets, for cross-batch de-duplication."""
    shas, hashes = set(), []
    for d in dirs:
        for r in csv.DictReader(open(Path(d) / 'labels.csv', encoding='utf-8')):
            shas.add(r['crop_sha256'])
            p = Path(d) / r['crop']
            if p.is_file():
                with Image.open(p) as im:
                    hashes.append((dhash(im), key(r['text']), f"{Path(d).name}:{r['review_id']}"))
    return shas, hashes


def contact_sheets(rows, out, per_page=30):
    font = ImageFont.load_default()
    paths = []
    for page in range(0, len(rows), per_page):
        tiles = []
        for r in rows[page:page + per_page]:
            with Image.open(out / r['crop']) as im:
                im = im.convert('RGB')
                im = im.resize((max(1, round(im.width * 56 / im.height)), 56))
                if im.width > 520:
                    im = im.resize((520, max(1, round(56 * 520 / im.width))))
            tile = Image.new('RGB', (540, 56 + 34), 'white')
            tile.paste(im, (10, 0))
            ImageDraw.Draw(tile).text((10, 60), f"{r['review_id']}  [{r['field']}]  {r['text'].replace(chr(10), ' | ')}",
                                      fill='black', font=font)
            tiles.append(tile)
        sheet = Image.new('RGB', (540 * 2, 90 * ((len(tiles) + 1) // 2)), 'white')
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 2) * 540, (i // 2) * 90))
        path = out / f'contact_sheet_{page // per_page + 1:02d}.png'
        sheet.save(path)
        paths.append(path.name)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('batch', type=Path)
    ap.add_argument('--batch-id', required=True, help='Short letters/digits tag, e.g. B01; becomes review_id prefix')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--against', type=Path, action='append', default=[],
                    help='Earlier accepted set (labels.csv + crops/) to de-duplicate against; repeatable')
    ap.add_argument('--sample', type=int, default=60, help='Crops in the human spot-check sample')
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9]{1,12}', a.batch_id):
        raise SystemExit('--batch-id must be 1-12 letters/digits')
    out = a.out or a.batch / 'intake'
    if out.exists():
        raise SystemExit(f'{out} exists; choose a new --out')
    labels_path = a.batch / 'labels.csv'
    src = list(csv.DictReader(open(labels_path, encoding='utf-8-sig')))
    missing_cols = {'file', 'field', 'text'} - set(src[0] if src else [])
    if missing_cols:
        raise SystemExit(f'labels.csv lacks columns: {sorted(missing_cols)}')

    keys, provenance = held_keys()
    real_chars = set(''.join(r['text'] for r in csv.DictReader(open(REAL_LABELS, encoding='utf-8'))))
    prior_shas, prior_hashes = known_sets(a.against)
    seen_shas, seen_hashes = {}, []
    accepted, rejected = [], []
    out.mkdir(parents=True)

    for n, r in enumerate(src, 1):
        fname, field = (r.get('file') or '').strip(), (r.get('field') or '').strip()
        text = (r.get('text') or '').replace('\\n', '\n').strip()
        reasons, notes = [], []
        path = a.batch / fname
        raw = im = None
        if not fname or not path.is_file():
            reasons.append('missing_file')
        else:
            raw = path.read_bytes()
            try:
                im = Image.open(io.BytesIO(raw))
                im.load()
            except Exception:
                reasons.append('unreadable_image')
                im = None
        if field not in FIELDS:
            reasons.append('unknown_field')
        if not text:
            reasons.append('empty_text')
        if '[UNK]' in text or '?' in text:
            reasons.append('unknown_text_marker')
        if '\t' in text or '\r' in text:
            reasons.append('tsv_unsafe_text')
        if text and leaks(text, keys):
            reasons.append('held_out_text')
        if text and max(ctc_need(line) for line in text.split('\n')) > PADDLE_CTC_STEPS:
            reasons.append('over_ctc_limit')
        digest = sha(raw) if raw else None
        if digest and (digest in prior_shas or digest in seen_shas):
            reasons.append('duplicate_file')
        if im is not None:
            if min(im.size) < MIN_SIDE:
                reasons.append('too_small')
            if max(im.size) > LARGE_SIDE:
                notes.append('large_image')
            if (im.getexif() or {}).get(274, 1) != 1:
                notes.append('exif_rotation')
            h = dhash(im)
            for other, okey, oid in prior_hashes + seen_hashes:
                if bin(h ^ other).count('1') <= NEAR_DUP_BITS:
                    if okey == key(text):
                        reasons.append(f'near_duplicate:{oid}')
                        break
                    notes.append(f'similar_image_different_text:{oid}')
            if 'too_small' not in reasons and text:
                _, regions, _ = segment_lines(np.asarray(im.convert('RGB')))
                labels, how = pairing(text, len(regions))
                if labels is None:
                    reasons.append(f'line_count_mismatch:found_{len(regions)}_label_{text.count(chr(10)) + 1}')
                elif how:
                    notes.append('lines_joined')
        new_chars = sorted(set(text) - real_chars - {'\n'})
        if new_chars:
            notes.append('new_characters:' + ''.join(new_chars))

        if reasons:
            rejected.append(dict(row=n, file=fname, field=field, text=text, reasons=';'.join(reasons),
                                 notes=';'.join(notes)))
            continue
        rid = f'G{a.batch_id}_{len(accepted) + 1:05d}'
        rel = Path('crops') / field / f'{rid}{path.suffix.lower() or ".png"}'
        (out / rel.parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out / rel)
        if sha((out / rel).read_bytes()) != digest:
            raise SystemExit(f'Copy hash mismatch for {fname}')
        seen_shas[digest] = rid
        seen_hashes.append((h, key(text), rid))
        accepted.append(dict(review_id=rid, split='train', input_set='synthetic', field=field, crop=rel.as_posix(),
                             crop_sha256=digest, text=text, legibility='full', field_status='present',
                             label_source=f"ai_image_generator:{(r.get('generator') or 'unknown').strip()}",
                             human_check_status='pending_batch_spotcheck', scoring_eligible=False,
                             exclusion_reason='synthetic_training_only',
                             source_name=f"{a.batch.name}/{fname}|prompt:{(r.get('prompt_id') or '').strip()}",
                             note=';'.join(notes)))

    with (out / 'labels.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator='\n')
        w.writeheader()
        w.writerows(accepted)
    with (out / 'rejected.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['row', 'file', 'field', 'text', 'reasons', 'notes'], lineterminator='\n')
        w.writeheader()
        w.writerows(rejected)
    sample = sorted(random.Random(a.seed).sample(accepted, min(a.sample, len(accepted))), key=lambda r: r['review_id'])
    with (out / 'spotcheck.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['review_id', 'field', 'crop', 'label_text', 'verdict', 'human_reading',
                                          'reviewer', 'reviewed_at'], lineterminator='\n')
        w.writeheader()
        w.writerows(dict(review_id=r['review_id'], field=r['field'], crop=r['crop'], label_text=r['text'],
                         verdict='', human_reading='', reviewer='', reviewed_at='') for r in sample)
    sheets = contact_sheets(sample, out) if sample else []

    reason_counts = {}
    for r in rejected:
        for reason in r['reasons'].split(';'):
            base = reason.split(':')[0]
            reason_counts[base] = reason_counts.get(base, 0) + 1
    manifest = dict(script='scripts/intake_synthetic_batch.py', created=dt.datetime.now().isoformat(timespec='seconds'),
                    batch=str(a.batch), batch_id=a.batch_id, labels_sha256=sha(labels_path.read_bytes()),
                    rows=len(src), accepted=len(accepted), rejected=len(rejected), rejected_by_reason=reason_counts,
                    accepted_by_field={f: sum(r['field'] == f for r in accepted) for f in FIELDS},
                    against=[str(p) for p in a.against], held_out_keys=len(keys), held_out_sources=provenance,
                    ctc_limit=PADDLE_CTC_STEPS, near_duplicate_bits=NEAR_DUP_BITS,
                    spotcheck=dict(seed=a.seed, size=len(sample), file='spotcheck.csv', sheets=sheets,
                                   status='pending human review'),
                    limits=['Label-image agreement is not checked automatically; spotcheck.csv needs a human.',
                            'Held-out check is exact per line after normalisation, not substring or fuzzy.',
                            'No OCR model is run; hard crops are not removed.'])
    (out / 'intake_manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: manifest[k] for k in ('rows', 'accepted', 'rejected', 'rejected_by_reason',
                                               'accepted_by_field')}, indent=1))
    print(f'Output: {out}\nNext: a human fills {out / "spotcheck.csv"} using the contact sheets.')


if __name__ == '__main__':
    main()
