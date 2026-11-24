"""Merge human-confirmed test labels into the test review source for scoring.

Usage: python3 scripts/merge_test_labels.py TEST_SOURCE.csv TEST_LABELS.csv OUT.csv

TEST_SOURCE.csv holds crop identity/geometry with empty labels
(evaluation/ocr_review/test-20261116/test.source.csv). TEST_LABELS.csv is the
output of finalize_test_labels.py. Every source row must have exactly one
confirmed label with the same crop path; nothing is filled from AI proposals.
"""
import csv
import sys
from pathlib import Path

source, labels, out = map(Path, sys.argv[1:4])
if out.exists():
    raise SystemExit(f'{out} exists; refusing to overwrite')
with open(source, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    columns, rows = list(reader.fieldnames), list(reader)
confirmed = {r['review_id']: r for r in csv.DictReader(open(labels, encoding='utf-8'))}
if set(confirmed) != {r['review_id'] for r in rows} or len(confirmed) != len(rows):
    raise SystemExit('Source and label review IDs differ')
extra = ['review_status', 'reviewer', 'reviewed_at', 'reviewer_type', 'label_source']
for row in rows:
    label = confirmed[row['review_id']]
    if label['crop'] != row['crop']:
        raise SystemExit(f"Crop path differs for {row['review_id']}")
    if row['transcription'] or row['legibility'] or row['field_status']:
        raise SystemExit(f"Source already has a label for {row['review_id']}")
    row.update(transcription=label['text'], legibility=label['legibility'],
               field_status=label['field_status'], review_status='reviewed',
               reviewer=label['reviewer'], reviewed_at=label['reviewed_at'],
               reviewer_type='human', label_source=label['label_source'])
with open(out, 'x', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, columns + [c for c in extra if c not in columns], lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
full = sum(r['legibility'] == 'full' and '[unk]' not in r['transcription'].casefold() for r in rows)
print(f'wrote {out}: {len(rows)} rows; {full} full-legibility rows without [UNK]')
