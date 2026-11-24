# Import human OCR review decisions

## Recorded focused pairing check — 16 November 2026

`.cache/ocr_review/cody-pairing-20261116-01/` preserves the unchanged uploaded
41-row CSV, effective decisions, chat provenance, dry-run/import audits and
file-integrity checks. cody explicitly retained P033/P109 as `needs_resolution`
and confirmed the 13 previously blank rows were checked; those rows accept the
same-visible-text choices displayed on their review page. This is an AI-assisted
human check, not blind independent review. All 41 records have decisions:
29 same text, one different coverage, one exclusion and ten unresolved.

Use the cumulative `crop_pairing_decisions.current.csv` in this directory for
later imports, together with the earlier `validation.decisions.cody.csv` text
file and the existing group form. The cumulative form retains these 41 decisions
and the 73 candidates outside this review. A fresh blank pairing form would
lose the recorded pairing progress when rebuilding from original sources.
Text decisions and the previous 37 exclusions were preserved; P028 adds the
38th exclusion. No photo-group acceptance was inferred.

## Recorded validation text check — 16 November 2026

The user confirmed all validation crops on `check_my_proposals.html` looked good
after inspection and provided reviewer name **cody**. Recorded as AI-assisted
human checking with no reported edits, not independent blind adjudication.
`.cache/ocr_review/cody-validation-20261116-01/validation.decisions.cody.csv`
contains 253 accepted defaults and 18 retained unresolved field/presence decisions.
The neighbouring provenance file records the chat attestation. All original
exclusions and hashes remain intact. Group/pair and training review were not
inferred from this confirmation; numerical values are unchanged and verified
eligibility remains pending metadata review.

For the integrated command below, use this recorded cody text file with the same
original review/policy bindings when importing later group/pair decisions.

## Integrated metadata import — 15 November 2026

`scripts/import_ocr_metadata_decisions.py` now supports text decisions plus
source-photo grouping and crop correspondence in one audited export. The current
supported form set is `.cache/ocr_review/import-ready-20261115-01/`:

| Form | Reviewer-entered fields |
| --- | --- |
| `valid.text.decisions.csv` | The existing human text schema documented below. Use `correct` and final visible text when completing the blind template; leave uncertain cases `needs_resolution`, or record partial/illegible truth without promoting it into primary scoring. |
| `photo_group_decisions.csv` | `human_group_decision`: `confirm`, `exclude`, or `needs_resolution`; `human_group_id` for confirmed groups; `human_reviewer`, `human_reviewer_type=human`, `human_reviewed_at`, `human_notes`. |
| `crop_pairing_decisions.csv` | `human_correspondence`: `same_visible_text`, `different_visible_text`, `no_match`, `needs_resolution`, or `exclude`; the same human identity/type/date/notes fields. |

Keep immutable identities, hashes and `source_bundle_sha256` unchanged. Prefer
the `human_*` fields; legacy final-decision aliases, if supplied, must agree.
Blank decisions leave rows pending, and partial submissions are permitted.
For `no_match`, leave `annotation_id`, `annotation_crop` and
`annotation_crop_sha256` blank. The fresh template clears P005's zero-IoU
diagnostic annotation target. A replacement accepted annotation target must have
its correct ID, crop path and hash, originate from the same image/split and
overlap the prediction. Annotation labels are never copied into predicted text.

The bundle binds exact original review sources, policy overlays, canonical pair
and group inventories, and the split registry. Text decisions stay bound to the
original source review, while later policy exclusions are preserved. Human group
decisions propagate to all crops belonging to that source photo; confirming one
variant does not silently sign off other photos. Conflicting group IDs for the
same source family/hash are rejected. Accepted groups spanning splits, including
known exact source-name/hash links to test registry metadata, are excluded from
primary scoring. Registry checks do not prove unknown related-scene or historical
model-training independence. Group confirmation never removes existing exclusions.
No test image bytes or model weights are loaded.

Current command inputs (use unchanged paths to preserve form bindings):

```sh
.venv/bin/python scripts/import_ocr_metadata_decisions.py apply \
  --review evaluation/ocr_review/human-verification-20261113/training.source.csv \
  --review evaluation/ocr_review/human-verification-20261113/validation.source.csv \
  --policy-review .cache/ocr_review/conservative-exclusions-20261115-01/training.review.csv \
  --policy-review .cache/ocr_review/conservative-exclusions-20261115-01/validation.review.csv \
  --source-policy .cache/ocr_review/conservative-exclusions-20261115-01/source_groups.review.csv \
  --group-source .cache/ocr_review/closure-20261114-01/source_groups.ai.csv \
  --pair-source .cache/ocr_review/closure-20261114-01/correspondence.ai.csv \
  --split-registry evaluation/ocr_review/source-split-audit-20261113/sources.csv \
  --text-decisions .cache/ocr_review/cody-validation-20261116-01/validation.decisions.cody.csv \
  --groups .cache/ocr_review/import-ready-20261115-01/photo_group_decisions.csv \
  --pairings .cache/ocr_review/import-ready-20261115-01/crop_pairing_decisions.csv \
  --output .cache/ocr_review/HUMAN-REVIEW-NEW \
  --dry-run
```

After validation, remove `--dry-run` to publish a new export. Existing outputs
are refused; invalid later decisions publish no partial changes. The export
contains `train.review.csv`, `valid.review.csv`, `source_groups.csv`,
`unresolved.csv`, `audit.json` and `change_log.json`. Original sources and
input decisions are unchanged. Each operation recomputes scoring gates and keeps
`training_ready=false`. Use `template` with the same source flags and a fresh
output directory to prepare new bound forms.

Observed run on the inspected returns: `.cache/ocr_review/imported-20261115-01/`.
All final decision columns were empty; zero text/group/pair decisions applied.
2,188 rows retained, 37 validation exclusions preserved, 50 source photos retain
policy exclusion. Validation eligibility remains zero. Saved-run raw/normalised
baseline reports are in `baseline-status/`, with pending accuracy. The inspected
text sidecar was identity/hash checked and contained no final decisions; no AI
proposal was converted into a human acceptance. Its mapping audit accompanies
the fresh text template.

Synthetic verification:

```sh
.venv/bin/python -m unittest tests.evaluation.test_metadata_review \
  tests.evaluation.test_review_decisions tests.evaluation.test_crop_scoring -q
```

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
