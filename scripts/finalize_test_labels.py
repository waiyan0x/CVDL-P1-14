"""Turn an exported confirm-page CSV into evaluation/ocr_review/test_labels.csv.

Refuses unless every test crop was confirmed by a human. Also reports how often
the AI proposal was corrected (cite this beside the test scores).

Usage: python3 scripts/finalize_test_labels.py DATASET_DIR CONFIRMED.csv OUT.csv
"""
import csv
import sys
from pathlib import Path

dataset, confirmed, out = map(Path, sys.argv[1:4])
expected = {r['review_id']: r for r in csv.DictReader(open(dataset / 'labels.csv', encoding='utf-8'))
            if r['split'] == 'test'}
got = {r['review_id']: r for r in csv.DictReader(open(confirmed, encoding='utf-8-sig'))}
missing = sorted(set(expected) - set(got))
if missing:
    raise SystemExit(f'{len(missing)} test crops not confirmed yet, e.g. {missing[:5]}')
if out.exists():
    raise SystemExit(f'{out} exists; refusing to overwrite')
cols = ['review_id', 'crop', 'field', 'input_set', 'text', 'legibility', 'field_status',
        'label_source', 'reviewer', 'reviewed_at']
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, cols, lineterminator='\n')
    w.writeheader()
    for rid, e in expected.items():
        g = got[rid]
        w.writerow(dict(review_id=rid, crop=e['crop'], field=e['field'], input_set=e['input_set'],
                        text=g['text'], legibility=g['legibility'], field_status=g['field_status'],
                        label_source='claude_ai_proposal_human_corrected' if g['changed'] == 'yes'
                        else 'claude_ai_proposal_human_confirmed',
                        reviewer=g['reviewer'], reviewed_at=g['reviewed_at']))
changed = sum(g['changed'] == 'yes' for g in got.values() if g['review_id'] in expected)
print(f'wrote {out}: {len(expected)} rows; AI proposal corrected on {changed} ({100 * changed / len(expected):.1f}%)')
