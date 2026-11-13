# Prepare and return OCR verification

## Current working package

**Project decision, user instruction, 13 November 2026:** mixed-field crops and
operational messages remain a separate challenge set, excluded from primary
field scoring and training until field ownership is confirmed. Preserve supplied
classes; service identifiers, destination and route/road text remain distinct.
Do not classify an operational message as a service identifier merely because
it appears in a number box. Road text ownership still needs the annotation guide.

The [verification package](../evaluation/ocr_review/human-verification-20261113/)
contains 1,917 training and 271 validation rows. Its working snapshots preserve
the previous AI proposals and add explicit exclusions for 35 training and 26
validation challenge crops. These are project-policy exclusions, not new human
text or field attestations. Original review files are unchanged. The other
flagged rows, including field mismatches and unreadable fields, remain unresolved.

## What the human reviewer does

1. Open [training.html](../evaluation/ocr_review/human-verification-20261113/training.html).
   Each ID shows its crop and supplied field without AI text. Click for native
   viewing. Read each variant independently; do not complete it from other
   variants, route data, filenames or model predictions.
2. Copy `training.decisions.template.csv` to `training.decisions.YOUR_NAME.csv`.
   Keep `review_id`, `crop_sha256` and `source_review_sha256` unchanged. Import
   all CSV columns as text to preserve service identifiers and leading zeros.
3. Fill only rows you have inspected. For a resolved text decision, enter:

   | Column | Value |
   | --- | --- |
   | `human_decision` | `correct` to explicitly submit the final label, even when it happens to agree with the hidden AI proposal |
   | `final_transcription` | Visible text under [the transcription rules](OCR_TRANSCRIPTION_RULES.md); actual line breaks, case and punctuation preserved |
   | `final_legibility` | `full`, `partial`, `illegible`, or `not_applicable` |
   | `final_field_status` | `present`, `blank`, `absent`, or `wrong_field` |
   | `human_field_confirmation` | `confirmed` only if the supplied field assignment is confirmed; otherwise `needs_resolution` |
   | `human_crop_treatment` | `single_field`, `challenge`, or `needs_resolution`; use `challenge` for the policy-excluded cases |
   | `human_reviewer` | Your actual name |
   | `human_reviewer_type` | `human` |
   | `human_reviewed_at` | Actual review date, for example `YYYY-MM-DD`, or an ISO timestamp |
   | `human_notes` | Brief reason for your decision; required |

   Full text contains no `[UNK]`; partial text contains readable text and at least
   one `[UNK]`; illegible is exactly `[UNK]`. Blank/absent require empty text and
   `not_applicable`. Do not invent missing characters or expand abbreviations.
4. If you cannot resolve text/field ownership, use `human_decision=needs_resolution`,
   leave all `final_*` cells blank, set confirmation/treatment to `needs_resolution`
   (or treatment `challenge` where applicable), and fill identity/date/notes.
   To exclude an invalid crop, use `exclude`, leave `final_*` blank and give the
   exclusion reason in notes. Leave uninspected rows entirely blank after hashes.
5. Save UTF-8 CSV, preserving quoted multiline cells. Partial batches are allowed.
   Return the CSV path in chat. Validation uses `validation.html` and
   `validation.decisions.template.csv` in the same way; the existing 77 flagged
   IDs remain visible in the earlier adjudication queue.

The smaller [27-crop batch](../evaluation/ocr_training/v4-human-verification-01/README.md)
is still useful for practice, but has a different submission schema. Use the new
decision template for the import commands below; do not paste its older columns
into the importer.

## Validate and import a completed file

From the repository root, with the actual reviewer filename:

```sh
python3 scripts/import_ocr_review_decisions.py apply \
  --source evaluation/ocr_review/human-verification-20261113/training.source.csv \
  --decisions evaluation/ocr_review/human-verification-20261113/training.decisions.YOUR_NAME.csv \
  --dry-run
```

After a successful dry run, replace `--dry-run` with
`--output evaluation/ocr_review/training-human-YOUR_NAME-01` to save a new export.
Existing outputs are refused. For validation, substitute `validation` in both
input filenames and choose a separate output directory.

Import preserves immutable crop metadata and exclusions, records the decisions,
and reports remaining blockers. It always leaves `training_ready=false`.
Human text verification does not resolve source grouping, protected holdout
lineage, predicted-crop correspondence or approval of a training manifest.

## Source and split evidence

**Observed implementation/evidence:** the restored dataset directory was found at
`/Users/tanyilin/Downloads/2026-11-05-roboflow-v4-reviewed`. All 788 train/valid
photo byte hashes and handoff joins match; both COCO hashes match the supplied
OCR manifests. Across 735 train, 53 valid and 53 test metadata entries, there
are no cross-split exact-hash or exact-source-name links. Test photo hashes are
metadata attestations only; no test photo bytes were read or decoded.
See [audit.json](../evaluation/ocr_review/source-split-audit-20261113/audit.json).

This does not establish scene/burst independence. The existing 84-source,
28-group, 288-text-row legacy-holdout quarantine remains in place. Full-photo
scene grouping and review of different-name related captures remain open.
The three restored training variants associated with T0919/T0921/T0924/T0926/
T0929/T0931 were visually inspected by Codex (AI): they depict the same bus scene,
but the number-labelled patches remain too blurred to resolve field/text targets.
No new readable text, blank/absent state or human attestation is asserted.
Context sheet: `source-split-audit-20261113/training_presence_context.png`.

Reproduce the metadata/byte-identity audit into a new output directory:

```sh
python3 scripts/audit_ocr_source_splits.py \
  --dataset /Users/tanyilin/Downloads/2026-11-05-roboflow-v4-reviewed \
  --training-manifest evaluation/ocr_training/v4-reviewed-01-ai-01/source_manifest.json \
  --validation-manifest evaluation/ocr_annotations/v4-reviewed-01/source/manifest.json \
  --output evaluation/ocr_review/source-split-audit-NEW
```

The audit reads test COCO/preparation metadata only. Its train/valid hash checks
do not decode images. Neither this audit nor the blank verification package
finishes human adjudication, establishes OCR accuracy, or authorises training.
