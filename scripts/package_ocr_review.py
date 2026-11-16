"""Create an offline reviewer ZIP with embedded crops and no AI transcriptions."""

import argparse
import base64
import csv
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.evaluation.review_decisions import DECISION_COLUMNS, digest, load_source, read_rows

README = """# Portable OCR review

Extract the ZIP, then open training.html or validation.html in a web browser.
Every crop is embedded in its page. Original PNGs are also included under crops/,
using neutral review IDs. No connection to the producer's computer is required.
For another computer or service, transfer this ZIP, not the old HTML links.
If a service does not display embedded HTML images, use the included PNGs.

The supplied class and challenge policy are metadata, not verified human labels.
Read each crop independently; preserve case, punctuation, abbreviations and real
line breaks. Do not complete text from another variant, route knowledge or OCR.
Use [UNK] for each unresolved span; partial requires readable text plus [UNK],
and fully illegible is exactly [UNK]. Blank/absent needs explicit state and empty
text. Unknown field ownership remains needs_resolution. Never guess a label.

Copy the appropriate decisions.template.csv to a reviewer-named file and fill
only inspected rows. Keep review_id, crop_sha256 and source_review_sha256 unchanged.
For an actual human decision: human_decision=correct, final_transcription=visible
text, final_legibility=full/partial/illegible/not_applicable,
final_field_status=present/blank/absent/wrong_field,
human_field_confirmation=confirmed/needs_resolution,
human_crop_treatment=single_field/challenge/needs_resolution.
Add your actual name in human_reviewer, human_reviewer_type=human, the actual ISO
date in human_reviewed_at and a brief
decision reason in human_notes. For an unresolved decision use
human_decision=needs_resolution, leave final_* blank and explain in notes.
Leave uninspected decision cells blank. The HTML does not save edits.

Only a person who inspected the images may attest human review. Claude, Codex or
another AI must not fill a human identity/type or impersonate a human reviewer.
Any AI readings must be saved separately with reviewer_type=AI; they remain
proposals and do not pass human-review gates. Hiding AI text reduces suggestion
bias but does not establish reviewer independence or human provenance.

Return the completed decision CSV, including partial batches. The source-review
hashes bind the original maintainer snapshots, which remain in the repository.
Those snapshots contain prior AI proposals and are deliberately not shipped in
this reviewer package. Grouping, split overlap, prediction correspondence and
field adjudication remain separate gates. Test crops are not included.
"""


def package(workspace, validation_root, output):
    if output.exists() or output.with_suffix('.zip').exists():
        raise FileExistsError("Output directory or ZIP already exists")
    loaded = []
    for population in ('training', 'validation'):
        source = workspace / f'{population}.source.csv'
        template = workspace / f'{population}.decisions.template.csv'
        _, rows = load_source(source)
        source_hash = digest(source)
        columns, decisions = read_rows(template)
        if tuple(columns) != DECISION_COLUMNS or len(decisions) != len(rows):
            raise ValueError("Unexpected decision template schema/population")
        by_id = {r['review_id']: r for r in rows}
        if set(by_id) != {r['review_id'] for r in decisions}:
            raise ValueError("Template/source ID mismatch")
        for decision in decisions:
            row = by_id[decision['review_id']]
            if (decision['source_review_sha256'] != source_hash
                    or decision['crop_sha256'] != row['crop_sha256']
                    or any(decision[k] for k in DECISION_COLUMNS[3:])):
                raise ValueError("Template is not blank or hash-bound to this source")
        allowed_split = 'train' if population == 'training' else 'valid'
        if any(r['split'] != allowed_split for r in rows):
            raise ValueError("Reserved test or wrong split in reviewer source")
        loaded.append((population, source, template, rows))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.portable-review-', dir=output.parent) as temp:
        stage = Path(temp) / 'package'
        stage.mkdir()
        index = []
        for population, source, template, rows in loaded:
            folder = stage / 'crops' / population
            folder.mkdir(parents=True)
            cards = []
            for row in rows:
                rid = row['review_id']
                if not re.fullmatch(r'[ATP][0-9]+', rid):
                    raise ValueError("Unsafe review ID")
                crop = Path(row['crop_local_path']) if population == 'training' else validation_root / row['crop']
                data = crop.read_bytes()
                if hashlib.sha256(data).hexdigest() != row['crop_sha256'] or not data.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError(f"Crop hash/PNG mismatch: {rid}")
                target = folder / f'{rid}.png'
                target.write_bytes(data)
                uri = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
                policy = row.get('user_scope_policy', 'review_required')
                cards.append(f'<article id="{rid}"><h2>{rid}</h2><p>Supplied field: '
                             f'{escape(row["label"])}; policy: {escape(policy)}</p>'
                             f'<img src="{uri}" alt="Crop {rid}" loading="lazy">'
                             f'<p><a href="crops/{population}/{rid}.png">Open original PNG</a></p></article>')
                index.append(dict(population=population, review_id=rid, supplied_field=row['label'],
                                  scope_policy=policy, crop=f'crops/{population}/{rid}.png',
                                  crop_sha256=row['crop_sha256']))
            (stage / f'{population}.html').write_text(
                '<!doctype html><meta charset="utf-8"><title>Portable crop review</title>'
                '<style>body{font:16px sans-serif;margin:24px}article{border-top:1px solid #aaa;padding:20px 0}'
                'img{image-rendering:pixelated;min-width:240px;max-width:95vw}</style>'
                '<h1>'+population.title()+' crop review</h1><p>Images embedded; no remote connection needed. '
                'Read README.md before recording decisions. AI transcriptions and OCR predictions are not included. '
                'Only an actual person may attest human review. This page does not save edits.</p>'+''.join(cards))
            shutil.copyfile(template, stage / template.name)
        with (stage / 'crop_index.csv').open('x', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(index[0]))
            writer.writeheader()
            writer.writerows(index)
        (stage / 'README.md').write_text(README)
        audit = dict(rows={name:len(rows) for name, _, _, rows in loaded},
                     source_review_sha256={name:digest(source) for name, source, _, _ in loaded},
                     embedded_images=len(index), included_native_pngs=len(index), human_decisions_supplied=0,
                     ai_transcriptions_included=False, scoring_ready_rows=0, training_ready_rows=0,
                     test_images_accessed=False,
                     files_sha256={str(p.relative_to(stage)):digest(p) for p in sorted(stage.rglob('*')) if p.is_file()})
        (stage / 'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
        stage.rename(output)
    shutil.make_archive(str(output), 'zip', root_dir=output.parent, base_dir=output.name)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--validation-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = package(args.workspace, args.validation_root, args.output)
    print(json.dumps({k:v for k,v in result.items() if k != 'files_sha256'}, indent=2))
