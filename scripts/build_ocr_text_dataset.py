"""Build one OCR text-label dataset (crop image -> visible text) for train/valid/test.

Usage: build_dataset.py REPO OUT_DIR TEST_PROPOSALS_TSV SCORING_TEXT_RECORDS_CSV
"""
import csv, hashlib, os, shutil, sys, collections, json

repo, out, test_tsv, text_records = sys.argv[1:5]
pkg = os.path.join(repo, '.runtime/ocr-task-files-20261116')
FIELD = {'front_eds_num': 'bus_number', 'front_eds_destination': 'destination', 'front_eds_route': 'route_text'}
COLS = ['review_id', 'split', 'input_set', 'field', 'crop', 'crop_sha256', 'text', 'legibility', 'field_status',
        'label_source', 'human_check_status', 'scoring_eligible', 'exclusion_reason', 'source_name', 'note']

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def copy(src_abs, split, sub):
    rel = os.path.join('crops', split, sub, os.path.basename(src_abs))
    dst = os.path.join(out, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src_abs, dst)
    return rel

def eligibility(text, legibility, field_status, challenge):
    reasons = []
    if challenge: reasons.append('challenge_only')
    if field_status != 'present': reasons.append(field_status or 'field_status_missing')
    if legibility != 'full': reasons.append('legibility_not_full')
    if '[UNK]' in text: reasons.append('unknown_text')
    if field_status == 'present' and not text.strip(): reasons.append('empty_text')
    return (not reasons), ';'.join(reasons)

rows = []

# ---- train: 387 Codex labels, 3-copy consensus ----
src = {r['crop'].split('/')[-1]: r for r in csv.DictReader(open(os.path.join(pkg, 'labels/training.source.csv')))}
spot = {r['crop'].split('/')[-1] for r in csv.DictReader(open(os.path.join(pkg, 'human_review/train_spotcheck/checks.csv')))}
for r in csv.DictReader(open(os.path.join(repo, 'evaluation/ocr_training/train_labels_final.csv'))):
    s = src[r['crop'].split('/')[-1]]
    p = os.path.join(repo, r['crop'])
    rows.append(dict(review_id=s['review_id'], split='train', input_set='annotation', field=r['field'],
                     crop=copy(p, 'train', s['label']), crop_sha256=sha(p), text=r['text'], legibility='full',
                     field_status='present', label_source='codex_ai_3copy_consensus',
                     human_check_status='spotcheck_sampled_pending' if os.path.basename(p) in spot else 'not_sampled',
                     scoring_eligible='True', exclusion_reason='', source_name=r['source_name'], note=''))

# ---- valid: 258 rows (194 user-typed + 77 Codex, minus 13 train-scene overlaps) ----
vsrc = {r['review_id']: r for r in csv.DictReader(open(os.path.join(pkg, 'labels/validation.source.csv')))}
origin = {'Codi': 'human_typed_by_team', 'Codex': 'codex_ai'}
review_path = os.path.join(repo, 'evaluation/ocr_review/human-verification-20261116/validation.source.corrected-P065.csv')
reviewed = {r['review_id']: r for r in csv.DictReader(open(review_path))} if os.path.isfile(review_path) else {}
for r in csv.DictReader(open(os.path.join(pkg, 'labels/validation_labels.proposals.csv'))):
    s = vsrc[r['review_id']]
    h = reviewed.get(r['review_id'])
    if h and h.get('reviewer_type') == 'human':
        r = dict(r, text=h['transcription'], legibility=h['legibility'], field_status=h['field_status'])
    p = os.path.join(pkg, r['crop'])
    ok, why = eligibility(r['text'], r['legibility'], r['field_status'], s['user_scope_policy'] == 'challenge_only')
    sub = os.path.join('ground_truth' if r['input_set'] == 'annotation' else 'predicted', s['label'])
    rows.append(dict(review_id=r['review_id'], split='valid', input_set=r['input_set'], field=r['field'],
                     crop=copy(p, 'valid', sub), crop_sha256=sha(p), text=r['text'], legibility=r['legibility'],
                     field_status=r['field_status'], label_source=origin[r['label_origin']],
                     human_check_status='human_verified' if h and h.get('reviewer_type') == 'human' else 'pending',
                     scoring_eligible=str(ok), exclusion_reason=why,
                     source_name=os.path.basename(s['image']),
                     note=('Human reviewer: ' + h['reviewer'] + '; prior text: ' + h.get('prior_transcription', '') + '; prior field: ' + h.get('prior_field_status', '')) if h and h.get('reviewer_type') == 'human' else ''))

# ---- test: 118 annotation crops, Claude AI proposals ----
prop = {r['review_id']: r for r in csv.DictReader(open(test_tsv), delimiter='\t')}
for r in csv.DictReader(open(os.path.join(pkg, 'labels/test_labels.csv'))):
    t = prop[r['review_id']]
    text = t['text'].replace('\\n', '\n')
    p = os.path.join(pkg, r['crop'])
    ok, why = eligibility(text, t['legibility'], 'present', False)
    rows.append(dict(review_id=r['review_id'], split='test', input_set='annotation', field=r['field'],
                     crop=copy(p, 'test', r['crop'].split('/')[-2]), crop_sha256=sha(p), text=text,
                     legibility=t['legibility'], field_status='present', label_source='claude_ai_proposal',
                     human_check_status='pending', scoring_eligible=str(ok), exclusion_reason=why,
                     source_name=os.path.basename(r['crop']).split('_jpg')[0] + '.jpg', note=t['note']))

# ---- cross-check valid eligibility against the repo scorer ----
scorer = {}
for r in csv.DictReader(open(text_records)):
    scorer[r['review_id']] = r['scoring_eligible']
mismatch = [r['review_id'] for r in rows if r['split'] == 'valid' and scorer.get(r['review_id']) != r['scoring_eligible']]

with open(os.path.join(out, 'labels.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)

summary = collections.Counter((r['split'], r['input_set'], r['field'], r['scoring_eligible']) for r in rows)
stats = {f'{k[0]}/{k[1]}/{k[2]}/eligible={k[3]}': v for k, v in sorted(summary.items())}
json.dump(dict(rows=len(rows), counts=stats, valid_eligibility_mismatch_vs_repo_scorer=mismatch),
          open(os.path.join(out, 'summary.json'), 'w'), indent=1)
print(len(rows), 'rows; valid eligibility mismatches vs repo scorer:', mismatch)
for k, v in stats.items(): print(f'  {k}: {v}')
