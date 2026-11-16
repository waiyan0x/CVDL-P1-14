"""Apply a completed validation human-review export to the validation source CSV.

The human answer replaces transcription/legibility/field_status for every
reviewed row. The label it replaces is kept in the prior_* columns; the older
source file stays in git as the full history. Crop paths in the export are
ignored: rows are matched by review_id and checked against the expected field.

Usage:
  python3 scripts/apply_validation_human_review.py SOURCE.csv HUMAN_EXPORT.csv OUT.csv
"""
import csv
import sys
from pathlib import Path

source, export, out = map(Path, sys.argv[1:4])
if out.exists():
    raise SystemExit(f'{out} exists; refusing to overwrite')
FIELD = {'front_eds_num': 'bus_number', 'front_eds_destination': 'destination', 'front_eds_route': 'route_text'}

with open(source, encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    columns, rows = reader.fieldnames, list(reader)
human = {r['review_id']: r for r in csv.DictReader(open(export, encoding='utf-8-sig', newline=''))}

unknown = set(human) - {r['review_id'] for r in rows}
if unknown:
    raise SystemExit(f'export has review_ids not in source: {sorted(unknown)[:5]}')

applied = 0
for row in rows:
    h = human.get(row['review_id'])
    if h is None:
        continue
    if FIELD[row['label']] != h['field']:
        raise SystemExit(f"{row['review_id']}: field mismatch {row['label']} vs {h['field']}")
    t, leg, st = h['text'], h['legibility'], h['field_status']
    if leg == 'full' and (not t.strip() or '[UNK]' in t) or leg == 'partial' and '[UNK]' not in t \
            or leg == 'illegible' and t != '[UNK]':
        raise SystemExit(f"{row['review_id']}: text/legibility rule broken: {t!r} {leg}")
    row.update(prior_transcription=row['transcription'], prior_legibility=row['legibility'],
               prior_field_status=row['field_status'], prior_review_status=row['review_status'],
               prior_reviewer=row['reviewer'], prior_reviewed_at=row['reviewed_at'])
    row.update(transcription=t, legibility=leg, field_status=st, reviewer=h['reviewer'],
               reviewed_at=h['reviewed_at'], reviewer_type='human', review_status='reviewed',
               human_verification_status='human_verified',
               notes=(row['notes'] + ' | ' if row['notes'] else '') + 'human visual review ' + h['reviewed_at'])
    applied += 1

with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, columns, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
print(f'{out}: {len(rows)} rows, {applied} human-reviewed')
