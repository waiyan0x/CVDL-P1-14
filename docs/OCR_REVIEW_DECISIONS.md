# Import human OCR review decisions

This command records human review decisions in a new export, preserves the
source review, and lists remaining scoring blockers. It does not open crop
images, run OCR, score predictions, or make data training-ready.

## Prepare a decision template

Use a full annotation, prediction or training review CSV as the source. Run
annotation and prediction imports separately. Keep generated files under a
local ignored directory such as `.cache/ocr_review/`.

```sh
mkdir -p .cache/ocr_review/decisions
.venv/bin/python scripts/import_ocr_review_decisions.py template \
  --source evaluation/ocr_annotations/v4-reviewed-01/submissions/codex-ai-20261112-01/annotation_ai.review.csv \
  --output .cache/ocr_review/decisions/annotation-human.csv
```

The template binds each ID to its crop hash and the exact source CSV hash.
Preserve those three values. If the source changes, create a new template and
review the changes; do not replace hashes mechanically. The older manually
prepared human templates have a different schema and must not be passed to this
command directly.

Open the corresponding native crop or review sheet and follow
[the transcription rules](OCR_TRANSCRIPTION_RULES.md). Do not resolve text from
OCR predictions, route references or another frame. Record actual reviewer
identity/date; AI review is not human verification.

## Fill the decisions

| Column | Value |
| --- | --- |
| `human_decision` | `accept`, `correct`, `needs_resolution`, or `exclude`; blank leaves the source row unchanged |
| `final_transcription` | For `correct`, supply complete visible text with actual newlines and `[UNK]` spans where needed |
| `final_legibility` | For `correct`, use `full`, `partial`, `illegible`, or `not_applicable` for blank/absent fields |
| `final_field_status` | For `correct`, use `present`, `blank`, `absent`, or `wrong_field` |
| `human_field_confirmation` | `confirmed` or `needs_resolution`; this does not change the supplied class |
| `human_crop_treatment` | `single_field`, `challenge`, or `needs_resolution` |
| `human_reviewer` | Actual reviewer identity |
| `human_reviewer_type` | Explicitly `human` |
| `human_reviewed_at` | Actual ISO date or timestamp |
| `human_notes` | Required decision reason, including any clipping, mixed text or uncertainty |

For `accept`, final-label cells may be blank or equal the source values. Use
`correct` for a changed value. Blank/absent fields require empty final text and
`not_applicable` legibility. `needs_resolution` and `exclude` retain source text;
leave their final-label cells blank and explain the decision in notes.

Use `challenge` for a crop containing mixed fields unless a human inspection
establishes that it really contains one complete target field. Do not declare
`single_field` merely to remove an exclusion. This command does not recrop images
or implement mixed-field reading order. A wrong-field observation does not
rename or move the crop.

Decisions may cover a subset of source IDs. Every submitted ID must be unique
and match its original hashes. Untouched source rows remain in the export.

## Validate before writing

```sh
.venv/bin/python scripts/import_ocr_review_decisions.py apply \
  --source evaluation/ocr_annotations/v4-reviewed-01/submissions/codex-ai-20261112-01/annotation_ai.review.csv \
  --decisions .cache/ocr_review/decisions/annotation-human.csv \
  --dry-run
```

A dry run validates decisions and prints aggregate blocker counts without
creating an export. It never fills reviewer information automatically. An
explicit human attestation is recorded as supplied, not independently verified.

## Save a new export

Repeat the same command with a new `--output` directory instead of `--dry-run`:

```sh
.venv/bin/python scripts/import_ocr_review_decisions.py apply \
  --source evaluation/ocr_annotations/v4-reviewed-01/submissions/codex-ai-20261112-01/annotation_ai.review.csv \
  --decisions .cache/ocr_review/decisions/annotation-human.csv \
  --output .cache/ocr_review/decisions/annotation-reviewed-01
```

The export contains `review.csv`, `unresolved.csv`, `audit.json` and
`change_log.json`. Existing output directories are refused. Changes are written
only after all submitted decisions pass validation.

`review_blocking_reasons` and `unresolved.csv` describe current blockers. Existing
source `issue_codes` remain historical diagnostics; importing a correction does
not rewrite the original issue list. The change log retains before/after rows.

Full, present, human-reviewed text still needs explicit field/crop confirmation,
confirmed grouping and, for predicted crops, resolved correspondence before
`scoring_ready=true`. Group and correspondence values are preserved; review of
those relationships remains a separate task. Panel text stays unscored.
`training_ready` is always false in this export; training eligibility requires
a separate approved manifest. Existing exclusion reasons are preserved.

The current session reserves test crops. Use this workflow for validation and
training reviews now; leave test decisions for the independent final-evaluation
workflow. Do not commit generated review exports or dataset content.

## Verify the implementation

```sh
.venv/bin/python -m unittest tests.evaluation.test_review_decisions -q
```

These tests use synthetic rows only; no dataset images or weights are needed.
