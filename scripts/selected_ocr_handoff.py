"""Final selected-model handoff implementation; invoked by prepare_ocr_matching_handoff.py.

Since 19 November 2026 validation OCR comes from the frozen layout v4-lines-v3
runs (-valid-layoutv3) scored in normalised-v8-layoutv3. The 17 November package
(.runtime/ocr-matching-final-20261117) used normalised-v5-step6-20261117 and the
v4-lines-v1 validation runs; see git history for that version of this script.
"""
import csv
import hashlib
import html
import io
import json
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.crop_scoring import build_report, normalise_text
from export_provisional_matching_inputs import covered, panel_ref

SNAPSHOT = ROOT / 'evaluation/ocr_scoring/normalised-v8-layoutv3'
VALID_SUFFIX = '-valid-layoutv3'  # frozen layout v4-lines-v3
RUN_DIR = {'train': '-train', 'valid': VALID_SUFFIX, 'test': '-test'}
VALID_METADATA = ROOT / '.runtime/ocr-task-files-20261116/metadata/validation_detector_manifest.json'
CLASS_ZIP = ROOT / '.runtime/ocr_class_dataset/v4-reviewed-01.zip'
FULL_ZIP = ROOT / '.runtime/brendan-ocr-handoff/ocr_handoff_v4-reviewed-01.zip'
WEIGHTS = ROOT / '.cache/finetuned/paddleocr'
FIELD = {'front_eds_num': 'bus_number', 'front_eds_destination': 'destination',
         'front_eds_route': 'route_text', 'front_eds': 'front_eds'}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_csv(path, rows, columns=None):
    with path.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, columns or list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def audit():
    manifest = json.loads((SNAPSHOT / 'manifest.json').read_text())
    config = json.loads((SNAPSHOT / 'comparison.json').read_text())
    rebuilt = build_report(manifest, config, SNAPSHOT)
    saved = json.loads((SNAPSHOT / 'scores/report.json').read_text())
    if rebuilt != saved:
        raise ValueError('Recomputed scoring report differs from published snapshot')
    runs = []
    for split in ('train', 'valid', 'test'):
        reference = None
        layout = None
        for model in ('easyocr', 'trocr', 'paddleocr'):
            for version in ('pretrained', 'finetuned'):
                root = ROOT / f'evaluation/ocr_runs/{model}-{version}{RUN_DIR[split]}'
                report = json.loads((root / 'report.json').read_text())
                preds = [json.loads(line) for line in (root / 'predictions.jsonl').read_text().splitlines()]
                identity = {p['review_id']: p['crop_sha256'] for p in preds}
                if len(identity) != len(preds) or report['status'] != 'complete':
                    raise ValueError(f'Incomplete/duplicate run: {root}')
                current_layout = report['frozen_line_layout']['sha256']
                if reference is None:
                    reference, layout = identity, current_layout
                if identity != reference or current_layout != layout:
                    raise ValueError(f'Inputs/layout differ: {root}')
                runs.append(dict(run=root.name, crops=len(preds), crop_identity_equal=True,
                                 layout_sha256=layout, report_sha256=sha(root / 'report.json'),
                                 predictions_sha256=sha(root / 'predictions.jsonl')))
    return manifest, dict(scoring_reproduced_exactly=True, runs=runs,
                          train_scores='diagnostic; unchanged AI labels and final human spot-check limitations',
                          test_selection='User-specified model selection on TEST; not independent final assessment')


def prepare(output):
    output = output.resolve()
    if output.exists() or output.with_suffix('.zip').exists():
        raise FileExistsError(output)
    manifest, audit_result = audit()
    output.mkdir(parents=True)
    for name in ('crops', 'reference', 'evaluation', 'weights/paddleocr', 'inference', 'review'):
        (output / name).mkdir(parents=True, exist_ok=True)
    inventory = {r['review_id']: r for r in manifest['rows'] if r['split'] in ('valid', 'test')}
    panels, panel_records = {}, []
    from PIL import Image
    with ZipFile(CLASS_ZIP) as class_zip, ZipFile(FULL_ZIP) as full_zip:
        test_meta = json.loads(class_zip.read('manifest.json'))['splits']['test']['crops']
        sources = []
        for im in json.loads(VALID_METADATA.read_text())['images']:
            for population, key in (('annotation', 'ground_truth'), ('prediction', 'predictions')):
                for panel in im[key]:
                    if panel['label'] == 'front_eds':
                        sources.append(('valid', population, im['image'], im['image_sha256'], panel))
        for p in test_meta:
            if p['label'] == 'front_eds':
                sources.append(('test', 'annotation', p['image'], p['image_sha256'], p))
        for split, population, image, image_hash, p in sources:
            crop = p['crop']
            rid = f"{split}_{population}_PANEL_{panel_ref(crop)}_{Path(image).stem}"
            display = f'{split}:{population}:{Path(image).stem}:{panel_ref(crop)}'
            rel = f'crops/{split}/{population}/front_eds/{Path(crop).name}'
            target = output / rel; target.parent.mkdir(parents=True, exist_ok=True)
            data = class_zip.read(crop) if split == 'test' else full_zip.read('valid/' + crop.removeprefix('ground_truth/'))
            target.write_bytes(data)
            with Image.open(io.BytesIO(data)) as im:
                width, height = im.size
            record = dict(review_id=rid, split=split, crop_set=population, field='front_eds',
                          crop_id=rel, crop_path=str(target), crop_sha256=sha(target),
                          source_image=image, source_image_sha256=image_hash, input_width=width, input_height=height,
                          box_xyxy=p['box_xyxy'], detector_confidence=p.get('confidence'),
                          candidate_display_id=display)
            panel_records.append(record)
            panels.setdefault((split, population, image), []).append(record)
        # Retain only the source photos needed for review; no re-export or detector run.
        photo_members = {Path(n).name: n for n in full_zip.namelist()
                         if n.startswith('source_coco/') and n.lower().endswith(('.jpg', '.png', '.jpeg'))}
        photo_paths = {}
        for r in inventory.values():
            key = (r['split'], r['image'])
            if key not in photo_paths:
                n = photo_members.get(r['image'])
                if n:
                    data = full_zip.read(n)
                    if hashlib.sha256(data).hexdigest() != r['source_image_sha256']:
                        raise ValueError('Source photo hash differs')
                    rel = f"review/photos/{r['split']}/{r['image']}"
                    target = output / rel; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data); photo_paths[key] = rel
    (output / 'inference/panel_inventory.json').write_text(json.dumps(panel_records, indent=2) + '\n')
    subprocess.run([str(ROOT / '.cache/paddle-baseline-env/bin/python'),
                    str(ROOT / 'scripts/run_selected_panel_ocr.py'), '--model-dir', str(WEIGHTS),
                    '--inventory', str(output / 'inference/panel_inventory.json'),
                    '--output', str(output / 'inference/panel_predictions.jsonl')], check=True)
    records, labels, review_rows = [], [], []
    run_hashes = {}
    for split in ('valid', 'test'):
        run = ROOT / f'evaluation/ocr_runs/paddleocr-finetuned{RUN_DIR[split]}'
        run_hashes[split] = dict(predictions_sha256=sha(run / 'predictions.jsonl'), report_sha256=sha(run / 'report.json'))
        predictions = [json.loads(line) for line in (run / 'predictions.jsonl').read_text().splitlines()]
        expected = {rid for rid, r in inventory.items() if r['split'] == split}
        if {p['review_id'] for p in predictions} != expected:
            raise ValueError('Saved run coverage differs')
        for p in predictions:
            r = inventory[p['review_id']]
            if p['crop_sha256'] != r['crop_sha256']:
                raise ValueError('Saved prediction hash differs')
            box = json.loads(r['box_xyxy'])
            candidates = sorted(((covered(box, panel['box_xyxy']), panel) for panel in
                                panels.get((split, r['crop_source'], r['image']), [])),
                                key=lambda x: x[0], reverse=True)
            accepted = [(coverage, panel) for coverage, panel in candidates if coverage >= .5]
            best = accepted[0] if accepted else None
            display = best[1]['candidate_display_id'] if best else f"{split}:{r['crop_source']}:{Path(r['image']).stem}:solo-{r['review_id']}"
            assignment = 'panel' if len(accepted) == 1 else 'ambiguous' if accepted else 'none'
            raw = p['raw_text']
            rel = f"crops/{split}/{r['crop_source']}/{r['label']}/{Path(r['crop']).name}"
            src = ROOT / ('evaluation/ocr_annotations/v4-reviewed-01/source' if split == 'valid'
                          else '.runtime/ocr-text-dataset-20261116') / r['crop']
            if sha(src) != r['crop_sha256']:
                raise ValueError('Crop pixels changed')
            target = output / rel; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, target)
            record = dict(record_id=f"paddleocr/finetuned/{r['review_id']}", review_id=r['review_id'],
                          model='paddleocr', variant='finetuned', provisional=False, split=split,
                          input_set=r['crop_source'], field=FIELD[r['label']], source_image=r['image'],
                          source_image_sha256=r['source_image_sha256'], crop=rel, crop_sha256=r['crop_sha256'],
                          box_xyxy=box, candidate_display_id=display, display_assignment=assignment,
                          display_ownership_status='geometry_candidate_unreviewed',
                          display_coverage=best[0] if best else None,
                          raw_ocr_text=raw, normalised_ocr_text=normalise_text(raw),
                          prediction_status=p['status'], error=p.get('error'), ocr_confidence=p.get('ocr_confidence'),
                          detector_confidence=float(r['detector_confidence']) if r.get('detector_confidence') else None)
            records.append(record)
            labels.append(dict(review_id=r['review_id'], split=split, input_set=r['crop_source'], field=FIELD[r['label']],
                               text=r['transcription'], legibility=r['legibility'], field_status=r['field_status'],
                               scoring_eligible=r['scoring_eligible'], exclusion_reason=';'.join(r['scoring_blockers']),
                               reviewer=r.get('reviewer', ''), reviewed_at=r.get('reviewed_at', '')))
            review_rows.append(dict(review_id=r['review_id'], split=split, input_set=r['crop_source'], field=FIELD[r['label']],
                                    candidate_display_id=display, assignment=assignment, coverage=record['display_coverage'],
                                    crop=rel, crop_sha256=r['crop_sha256'], source_image_sha256=r['source_image_sha256'],
                                    source_photo=photo_paths.get((split, r['image']), ''),
                                    box_xyxy=json.dumps(box), panel_box_xyxy=json.dumps(best[1]['box_xyxy']) if best else '',
                                    human_display_id='', human_decision='', reviewer='', reviewed_at=''))
    for p in map(json.loads, (output / 'inference/panel_predictions.jsonl').read_text().splitlines()):
        panel = next(r for r in panel_records if r['review_id'] == p['review_id'])
        records.append(dict(record_id=f"paddleocr/finetuned/{p['review_id']}", review_id=p['review_id'], model='paddleocr',
                            variant='finetuned', provisional=False, split=panel['split'], input_set=panel['crop_set'],
                            field='front_eds', source_image=panel['source_image'], source_image_sha256=panel['source_image_sha256'],
                            crop=panel['crop_id'], crop_sha256=panel['crop_sha256'], box_xyxy=panel['box_xyxy'],
                            candidate_display_id=panel['candidate_display_id'], display_assignment='panel_self',
                            display_ownership_status='panel_self', display_coverage=1.0,
                            raw_ocr_text=p['raw_text'], normalised_ocr_text=normalise_text(p['raw_text']),
                            prediction_status=p['status'], error=p.get('error'), ocr_confidence=p.get('ocr_confidence'),
                            detector_confidence=panel['detector_confidence']))
    if len({r['record_id'] for r in records}) != len(records):
        raise ValueError('Duplicate record IDs')
    forbidden = {'text', 'transcription', 'legibility', 'scoring_eligible', 'exclusion_reason', 'target', 'ai_text'}
    assert all(not forbidden.intersection(r) for r in records)
    (output / 'matching_inputs.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records))
    for split, name in (('valid', 'validation'), ('test', 'test')):
        write_csv(output / f'{name}_labels.csv', [r for r in labels if r['split'] == split])
    write_csv(output / 'review/display_ownership.csv', review_rows)
    write_csv(output / 'matching_outputs.template.csv', [dict(record_id=r['record_id'], matching_status='pending',
              matched_service='', matched_endpoint='', reference_row_numbers='', match_similarity='',
              matching_policy_id='', reason='') for r in records])
    shutil.copyfile(ROOT / 'data/bus_information.csv', output / 'reference/bus_information.csv')
    shutil.copyfile(ROOT / 'evaluation/OCR_RESULTS.md', output / 'evaluation/OCR_RESULTS.md')
    shutil.copyfile(ROOT / 'evaluation/OCR_RESULTS_SYNTHETIC.md', output / 'evaluation/OCR_RESULTS_SYNTHETIC.md')
    shutil.copyfile(ROOT / 'OCR_HANDOFF_TASKS.md', output / 'evaluation/OCR_HANDOFF_TASKS.md')
    shutil.copyfile(ROOT / 'scripts/verify_ocr_matching_handoff.py', output / 'verify_handoff.py')
    (output / 'evaluation/steps2-8_audit.json').write_text(json.dumps(audit_result, indent=2) + '\n')
    for p in WEIGHTS.iterdir():
        if p.is_file(): shutil.copyfile(p, output / 'weights/paddleocr' / p.name)
    # Portable one-crop inference dependencies and exact source, with no application/database setup.
    shutil.copyfile(ROOT / 'scripts/run_selected_panel_ocr.py', output / 'inference/run_selected_panel_ocr.py')
    for name in ('ocr_crop_baseline.py', 'ocr_line_layout.py', 'paddle_crop_reader.py'):
        target = output / 'backend/app/evaluation' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'backend/app/evaluation' / name, target)
    for name in ('backend/__init__.py', 'backend/app/__init__.py', 'backend/app/evaluation/__init__.py'):
        (output / name).write_text('')
    environment = ROOT / f'.cache/ocr_runs/paddleocr-finetuned{VALID_SUFFIX}/environment.json'
    if environment.exists(): shutil.copyfile(environment, output / 'inference/environment.json')
    for source, dest in [('evaluation/ocr_review/train-spotcheck-20261117/summary.v3.final.json', 'evaluation/training_spotcheck.json'),
                         ('evaluation/ocr_review/test-confirmation-20261117/test_confirm.cody.2026-11-17.csv', 'evaluation/test_human_return.csv')]:
        shutil.copyfile(ROOT / source, output / dest)
    write_review(output, review_rows)
    counts = Counter(f"{r['split']}/{r['input_set']}/{r['field']}" for r in records)
    summary = dict(model='paddleocr', variant='finetuned', training_run='20261117-031848', records=len(records),
                   counts=dict(counts), statuses=dict(Counter(r['prediction_status'] for r in records)),
                   display_assignments=dict(Counter(r['assignment'] for r in review_rows)),
                   display_ownership='Geometry proposals, unreviewed; not human-confirmed bus ownership',
                   whole_display_ocr='Automatic pixel-only segmentation; no panel transcriptions or accuracy claim',
                   manual_review='Confirm display ownership before combining fields; no further text-label return required',
                   source_run_hashes=run_hashes, audit=audit_result)
    (output / 'README.md').write_text(readme(summary))
    # Remove machine-specific paths from the portable inventory (predictions already omit crop_path).
    for r in panel_records: r['crop_path'] = r['crop_id']
    (output / 'inference/panel_inventory.json').write_text(json.dumps(panel_records, indent=2) + '\n')
    summary['files_sha256'] = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'handoff_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    junk = [p for p in output.rglob('*') if p.name in ('__pycache__', '.DS_Store', '.cache') or p.suffix == '.pyc']
    if junk:
        raise ValueError(f'Unexpected files in package: {junk[:5]}')
    shutil.make_archive(str(output), 'zip', output.parent, output.name)
    with ZipFile(output.with_suffix('.zip')) as z:
        if z.testzip(): raise ValueError('Archive CRC failed')
    return summary


def readme(summary):
    return f'''# Selected OCR handoff for inference matching

Fine-tuned PaddleOCR, run `20261117-031848`. This replaces the provisional pretrained handoff.
Selected on 45 human-reviewed test annotation crops: CER 8.2%, WER 19.1%, exact 82.2%.
This is TEST-based model selection under the user's rule, not an independent final estimate.
Round 2 (real + synthetic training lines, run `20261118-084149`) did not meet the replacement rule,
so this model is unchanged; see `evaluation/OCR_RESULTS_SYNTHETIC.md`.

Rebuilt 19 November 2026. Validation OCR uses frozen layout `v4-lines-v3`: A095/P034 (v2) and
A052/A094/P046/P087 (v3) now have one line each instead of a clipped fragment or no layout.
16 validation crops remain deliberately unresolved and appear as `prediction_status=error`.
Test OCR and model weights are the same as in the 17 November package.

Start with `matching_inputs.jsonl` ({summary['records']} records), `reference/bus_information.csv`,
and `matching_outputs.template.csv`. Labels are separate in `validation_labels.csv` and `test_labels.csv`;
join by `review_id`, then join matching results by `record_id`. Labels must never supply matcher candidates.
Validation has annotation and detector populations; test has annotation only. Never combine populations.
All saved crop OCR is retained, including excluded/failed crops. Use OCR only when `prediction_status=success`;
error records may preserve partial raw output for debugging. Scores are not calibrated correctness probabilities.

`front_eds` records are whole-display OCR and can share a candidate display ID with text fields.
Automatic panel line geometry has not been human reviewed; panel OCR has no transcription truth or accuracy score.
Unresolved segmentation remains an explicit error. No full-crop fallback or reference correction was used.
`candidate_display_id` is a geometry proposal (at least 50% text-box coverage), not human-confirmed ownership.
Review `review/display_ownership.html` and record decisions in `review/display_ownership.csv` before combining
fields as verified same-bus evidence. Prioritise none/ambiguous assignments; leave uncertain cases unresolved.
Keep individual field matching usable while ownership is unresolved. Photos and crops are included.

Manual text reviews are already returned: validation 258, test 118, training spot-check 50.
Four training readings conflict (S018/S041/S046/S050); training labels remain unchanged and train scores diagnostic.
The historical split/group limitations are recorded in `evaluation/OCR_RESULTS.md`; layout fixes in `evaluation/OCR_RESULTS_SYNTHETIC.md`.
No new compulsory review of 387 training labels is introduced by this handoff.

Weights are included in `weights/paddleocr/` with original hash provenance; no Drive link is needed to run this package.
Drive source: `DRIVE/CVDL-OCR-finetune/paddleocr/20261117-031848/best/`.
The connected Drive account did not expose this folder, so a shareable URL is not available in this package.
No sharing permissions were changed. Model files remain outside Git.

Run on one new crop from this directory, in the existing Paddle environment:

```sh
/path/to/paddle-environment/bin/python inference/run_selected_panel_ocr.py --model-dir weights/paddleocr --crop /path/to/new_crop.png --output new_crop_ocr.jsonl
```

`inference/environment.json` records installed versions from the successful saved validation run.
The command uses CPU, two threads, no MKLDNN, unchanged model hashes, shared grayscale line extraction,
RGB replication and native Paddle processing. New images use automatic pixel-only segmentation; saved
field benchmarks used their frozen layouts. Thus this command does not promise frozen-layout benchmark accuracy.
Raw outputs, panel line regions and errors are preserved; no matching is implemented here.

Matching is your next step: exact service strings (retain suffixes/zeros), fuzzy destination matching,
conflict/tie handling, and abstention. Road text stays separate because the reference has no road-name field.
Use same-display evidence only after resolving ownership. Tune cutoffs 25/50/75 and margin on validation,
freeze the policy, then evaluate matching on test once. Report raw versus matched exact match, acceptance,
accepted accuracy, rescued errors, harmful changes, valid-but-wrong service IDs and unresolved counts separately.

Observed cases to handle in matching (from validation OCR; proposals, not implemented here):
- Destination text often starts with a `>` arrow; strip it before comparing.
- Displays abbreviate (`INT`, `TER`, `MRT`, `NTH`, `AVE`, `RD`); the reference uses longer names such as
  "Choa Chu Kang Bus Interchange". Expand or normalise both sides before fuzzy scoring.
- A052/P046 show `14E` but OCR reads `148`, which is a different real service in the reference. A number
  that conflicts with the same display's destination must be flagged, not accepted on the number alone.
- PaddleOCR confidence is not a reliable gate on its own: some wrong readings score above 0.99.

`evaluation/steps2-8_audit.json` confirms all 18 runs share input hashes/layouts within each split and that
all six model scores reproduce the saved report exactly. `handoff_manifest.json` hashes every packaged file.
Verify the package with `python3 verify_handoff.py`; this checks files and label/display joins without loading OCR.
'''


def write_review(output, rows):
    """Provide source context and explicit human decisions without auto-confirming any row."""
    from PIL import Image
    cards = []
    for i, r in enumerate(rows):
        photo_path = r['source_photo'].removeprefix('review/')
        photo = html.escape(photo_path, quote=True)
        box = json.loads(r['box_xyxy'])
        panel = json.loads(r['panel_box_xyxy']) if r['panel_box_xyxy'] else None
        with Image.open(output / r['source_photo']) as im:
            width, height = im.size
        def rect(b, color):
            return f'<rect x="{b[0]}" y="{b[1]}" width="{b[2]-b[0]}" height="{b[3]-b[1]}" fill="none" stroke="{color}" stroke-width="3"/>'
        overlay = f'<svg viewBox="0 0 {width} {height}"><image href="{photo}" width="{width}" height="{height}"/>'
        overlay += (rect(panel, '#00ff55') if panel else '') + rect(box, '#ff3333') + '</svg>'
        priority = r['assignment'] != 'panel'
        cards.append(f'<details data-index="{i}" {"open" if priority else ""}><summary>{html.escape(r["review_id"])} — {r["assignment"]}</summary>'
                     f'<p>Red: text crop. Green: proposed panel. Source image is unchanged.</p>{overlay}'
                     f'<img loading="lazy" src="../{html.escape(r["crop"], quote=True)}">'
                     f'<p>Proposed display: {html.escape(r["candidate_display_id"])}</p>'
                     '<label>Decision <select data-key="human_decision"><option value="">Unreviewed</option>'
                     '<option>confirm_candidate</option><option>correct_display</option><option>unresolved</option></select></label>'
                     '<label>Corrected display ID <input data-key="human_display_id"></label></details>')
    # The original row order and immutable geometry/hash bindings travel in every exported decision.
    template = r'''<!doctype html><meta charset="utf-8"><title>Display ownership review</title>
<style>body{font:16px system-ui;max-width:1000px;margin:24px auto}svg{width:100%;max-height:650px}img{max-width:100%;max-height:130px}details{border-bottom:1px solid #aaa;padding:15px}summary{font-weight:bold}header{position:sticky;top:0;background:white;padding:12px;z-index:2}input{width:220px}</style>
<h1>Display ownership review</h1><p>Geometry proposals only. Start with P005, P035, P074 and P094 (expanded). Other rows can be opened for confirmation before treating groups as verified same-bus evidence. This is not another text-label review.</p>
<header><label>Your name <input id="reviewer"></label><label>Date <input id="date" type="date"></label><button id="export">Download ownership decisions</button><span id="progress"></span><small>Export before closing; this page does not autosave. Only rows with an explicit decision are exported.</small></header>
__CARDS__
<script>
const source=__ROWS__;
const cards=[...document.querySelectorAll('details')];
document.getElementById('export').onclick=()=>{
 const reviewer=document.getElementById('reviewer').value.trim(),date=document.getElementById('date').value;
 if(!reviewer||!date){alert('Enter your name and date');return;}
 const rows=cards.map((c,i)=>{const r={...source[i]};c.querySelectorAll('[data-key]').forEach(x=>r[x.dataset.key]=x.value);r.reviewer=reviewer;r.reviewed_at=date;return r;}).filter(r=>r.human_decision);
 if(!rows.length){alert('Record at least one decision');return;}
 if(rows.some(r=>r.human_decision==='correct_display'&&!r.human_display_id.trim())){alert('A correction needs a display ID');return;}
 const cols=Object.keys(source[0]);const q=v=>'"'+String(v??'').replaceAll('"','""')+'"';
 const csv=[cols,...rows.map(r=>cols.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\n')+'\n';
 const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='display_ownership.'+reviewer.replace(/[^a-zA-Z0-9_-]/g,'_')+'.'+date+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 document.getElementById('progress').textContent=rows.length+' decisions exported';
};
</script>'''
    page = template.replace('__CARDS__', ''.join(cards)).replace('__ROWS__', json.dumps(rows).replace('<', '\\u003c'))
    (output / 'review/display_ownership.html').write_text(page)
