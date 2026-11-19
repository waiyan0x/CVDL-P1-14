"""Round 2 scoring: pretrained | fine-tuned (real) | fine-tuned (real + synthetic).

Usage: .venv/bin/python scripts/build_round2_scoring.py OUTPUT_DIR

1. (top)      build_step6_scoring.py unchanged (normalised-v6 inputs: validation
              layout v4-lines-v2, train spot-check overrides). Pretrained vs round 1.
2. syn/       the same frozen manifest; baseline = pretrained, finetuned = the
              synthetic-bundle models (<model>-finetunedsyn-*). Missing runs are
              recorded as Unavailable, never filled in.
3. holdout/   route hold-out, full crops: same manifest as Table 4a, both rounds.
4. partial/   route hold-out partial crops, readable text only (diagnostic).
5. ROUND2_RESULTS.md: three-way tables plus the round 2 selection check.

Selection rule (user-confirmed in OCR_HANDOFF_TASKS.md): the round 1 app model stays unless
a synthetic-trained model wins at least two of CER/WER/exact on test (all fields)
against every other fine-tuned model AND is no worse in CER on validation
(annotation, all fields) and the route hold-out.
"""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from backend.app.evaluation.crop_scoring import build_report, write_report  # noqa: E402
import build_step6_scoring  # noqa: E402

RUNS = ROOT / 'evaluation/ocr_runs'
CACHE = ROOT / '.cache/ocr_runs'
HOLD = ROOT / 'evaluation/ocr_scoring/route-holdout-20261117'
HOLD_SOURCE = ROOT / 'evaluation/ocr_review/route-holdout-20261117/route_holdout_partial.inventory.csv'
MODELS = (('paddleocr', 'PaddleOCR'), ('trocr', 'TrOCR'), ('easyocr', 'EasyOCR'))
FIELDS = (('front_eds_num', 'number'), ('front_eds_destination', 'destination'),
          ('front_eds_route', 'route'), ('all', '**all fields**'))
COLS = ('pre', 'fine', 'fine+syn')


def syn_available(model):
    return all(p.is_dir() for p in (RUNS / f'{model}-finetunedsyn-valid-layoutv2',
                                    RUNS / f'{model}-finetunedsyn-test', CACHE / f'{model}-finetunedsyn-train'))


def filtered_train(src, dst, keep):
    dst.mkdir(parents=True)
    shutil.copy2(src / 'report.json', dst / 'report.json')
    lines = [x for x in (src / 'predictions.jsonl').read_text(encoding='utf-8').splitlines()
             if x.strip() and json.loads(x)['review_id'] in keep]
    if len(lines) != len(keep):
        raise SystemExit(f'{src.name} lacks predictions for some selected crops')
    (dst / 'predictions.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def cells(report):
    """{(model, variant): {(split, input_set, field): cell}}"""
    out = {}
    for m in report['models']:
        for v, d in m['variants'].items():
            out[m['id'], v] = {(c['split'], c['input_set'], c['field']): c for c in d['cells']}
    return out


def fmt(cell, key):
    if not cell or cell['status'] != 'Scored':
        return 'pending' if cell and cell['status'] == 'Unavailable' else '—'
    return f"{100 * cell[key]:.1f}"


def table(title, real, syn, split, input_set, note=''):
    lines = [f'### {title}', '', note, ''] if note else [f'### {title}', '']
    lines += ['| Model | Field | n | ' + ' | '.join(f'{m} {c}' for m in ('CER', 'WER', 'Exact') for c in COLS) + ' |',
              '| --- | --- | ---: |' + ' ---: |' * 9]
    for model, name in MODELS:
        for field, label in FIELDS:
            key = (split, input_set, field)
            trio = (real[model, 'baseline'].get(key), real[model, 'finetuned'].get(key), syn[model, 'finetuned'].get(key))
            if not trio[0] or trio[0]['status'] == 'No samples':
                continue
            vals = [fmt(c, k) for k in ('cer', 'wer', 'exact_match') for c in trio]
            lines.append(f'| {name} | {label} | {trio[0]["eligible"]} | ' + ' | '.join(vals) + ' |')
    return '\n'.join(lines) + '\n'


def main(out):
    out = Path(out).resolve()
    if out.parent != (ROOT / 'evaluation/ocr_scoring').resolve():
        raise SystemExit('OUTPUT_DIR must be directly under evaluation/ocr_scoring/ (step 6 run paths are relative)')
    build_step6_scoring.main(out)  # refuses an existing folder
    manifest = json.loads((out / 'manifest.json').read_text())
    keep = {r['review_id'] for r in manifest['rows'] if r['split'] == 'train'}

    # 2. synthetic-trained models on the same manifest.
    real_config = json.loads((out / 'comparison.json').read_text())
    syn_dir = out / 'syn'
    syn_dir.mkdir()
    syn_config = {'models': []}
    for entry in real_config['models']:
        model = entry['id']
        baseline = {'runs': [dict(r, run_dir=str((out / r['run_dir']).resolve())) for r in entry['baseline']['runs']]}
        if syn_available(model):
            filtered_train(CACHE / f'{model}-finetunedsyn-train', syn_dir / f'train_runs_filtered/{model}-finetunedsyn-train', keep)
            fine = {'runs': [
                {'run_dir': str(syn_dir / f'train_runs_filtered/{model}-finetunedsyn-train'), 'splits': ['train'], 'input_sets': ['annotation']},
                {'run_dir': str(RUNS / f'{model}-finetunedsyn-valid-layoutv2'), 'splits': ['valid'], 'input_sets': ['annotation', 'prediction']},
                {'run_dir': str(RUNS / f'{model}-finetunedsyn-test'), 'splits': ['test'], 'input_sets': ['annotation']}]}
        else:
            fine = {'status': 'Unavailable'}
        syn_config['models'].append({'id': model, 'baseline': baseline, 'finetuned': fine})
    (syn_dir / 'comparison.json').write_text(json.dumps(syn_config, indent=2) + '\n')
    write_report(build_report(manifest, syn_config, syn_dir), syn_dir / 'scores')

    # 3. route hold-out (full crops), both rounds.
    hold_manifest = json.loads((HOLD / 'manifest.json').read_text())
    hold_reports = {}
    for tag, fine_tag in (('real', 'finetuned'), ('syn', 'finetunedsyn')):
        config = {'models': []}
        for model, _ in MODELS:
            def spec(t):
                d = CACHE / f'{model}-{t}-routeholdout'
                return ({'run_dir': str(d), 'splits': ['train'], 'input_sets': ['annotation']}
                        if d.is_dir() else {'status': 'Unavailable'})
            config['models'].append({'id': model, 'baseline': spec('pretrained'), 'finetuned': spec(fine_tag)})
        hold_reports[tag] = build_report(hold_manifest, config, out)
        write_report(hold_reports[tag], out / f'holdout/{tag}')

    # 4. partial crops, readable text only.
    variants = ['pretrained', 'finetuned'] + (['finetunedsyn'] if all(
        (CACHE / f'{m}-finetunedsyn-routeholdout-partial').is_dir() for m, _ in MODELS) else [])
    subprocess.run([sys.executable, str(ROOT / 'scripts/score_partial_route.py'), str(HOLD_SOURCE), str(CACHE),
                    'routeholdout-partial', str(out / 'partial'), ','.join(variants)], check=True,
                   stdout=subprocess.DEVNULL)

    # 5. combined tables.
    real = cells(json.loads((out / 'scores/report.json').read_text()))
    syn = cells(json.loads((syn_dir / 'scores/report.json').read_text()))
    hreal, hsyn = cells(hold_reports['real']), cells(hold_reports['syn'])
    parts = ['# OCR results — round 2 (synthetic training data)', '',
             'pre = pretrained; fine = fine-tuned on real labels (run 20261117-031848); '
             'fine+syn = fine-tuned on real + synthetic lines (`ocr_finetune_bundle-20261118-syn.zip`). '
             '`pending` = synthetic-trained run not available yet. Normalised scoring; all values %.', '',
             table('Test annotation crops (official)', real, syn, 'test', 'annotation'),
             table('Validation annotation crops (official)', real, syn, 'valid', 'annotation',
                   'Validation also chose each model\'s training epoch, so fine-tuned values are optimistic.'),
             table('Validation detector crops (official)', real, syn, 'valid', 'prediction'),
             table('Route hold-out, full crops (supplementary)', hreal, hsyn, 'train', 'annotation',
                   'Single human reviewer; split shows as train because the crops come from train photos.'),
             table('Train (diagnostic only)', real, syn, 'train', 'annotation',
                   'AI labels; models were trained on these crops. Not an accuracy result.')]
    partial = list(csv.DictReader(open(out / 'partial/summary.csv', encoding='utf-8')))
    parts += ['### Route hold-out, partial crops — readable text only (diagnostic)', '',
              '| Model | Version | n | Readable-text CER | 95% range | All readable correct |',
              '| --- | --- | ---: | ---: | --- | ---: |']
    parts += [f"| {r['model']} | {r['version']} | {r['crops']} | {r['known_text_cer']} | {r['ci_low']}–{r['ci_high']} | "
              f"{r['all_readable_correct_pct']} |" for r in partial]
    parts += ['', selection(real, syn, hreal, hsyn)]
    (out / 'ROUND2_RESULTS.md').write_text('\n'.join(parts) + '\n', encoding='utf-8')
    print((out / 'ROUND2_RESULTS.md').read_text())


def selection(real, syn, hreal, hsyn):
    key = ('test', 'annotation', 'all')
    cands = {}
    for model, name in MODELS:
        cands[f'{name} fine'] = real[model, 'finetuned'].get(key)
        c = syn[model, 'finetuned'].get(key)
        if c and c['status'] == 'Scored':
            cands[f'{name} fine+syn'] = c
    lines = ['### Round 2 app-model check (agreed rule)', '',
             '| Fine-tuned model | Test CER | Test WER | Test exact |', '| --- | ---: | ---: | ---: |']
    lines += [f"| {n} | {100*c['cer']:.1f} | {100*c['wer']:.1f} | {100*c['exact_match']:.1f} |" for n, c in cands.items()]
    syn_names = [n for n in cands if n.endswith('fine+syn')]
    if not syn_names:
        return '\n'.join(lines + ['', '**No synthetic-trained model available yet; the round 1 app model '
                                  '(fine-tuned PaddleOCR) stands.**'])
    verdicts = []
    for n in syn_names:
        c = cands[n]
        others = [o for k, o in cands.items() if k != n]
        wins = all(sum([c['cer'] < o['cer'], c['wer'] < o['wer'], c['exact_match'] > o['exact_match']]) >= 2 for o in others)
        model = next(m for m, name in MODELS if n.startswith(name))
        v = ('valid', 'annotation', 'all')
        h = ('train', 'annotation', 'front_eds_route')
        no_worse_valid = syn[model, 'finetuned'][v]['cer'] <= real[model, 'finetuned'][v]['cer']
        hs, hr = hsyn.get((model, 'finetuned'), {}).get(h), hreal[model, 'finetuned'][h]
        no_worse_hold = bool(hs and hs['status'] == 'Scored' and hs['cer'] <= hr['cer'])
        verdicts.append(f'- {n}: beats every other fine-tuned model on test (2 of 3): {"yes" if wins else "no"}; '
                        f'validation CER no worse than its round 1 version: {"yes" if no_worse_valid else "no"}; '
                        f'route hold-out CER no worse: {"yes" if no_worse_hold else "no"} → '
                        f'**{"candidate to replace the app model" if wins and no_worse_valid and no_worse_hold else "does not replace"}**')
    return '\n'.join(lines + [''] + verdicts + ['', 'With 45 test crops one crop moves exact match by 2.2 points; '
                                                'choosing among more candidates on the same test set makes the winner look better than it is.'])


if __name__ == '__main__':
    main(sys.argv[1])
