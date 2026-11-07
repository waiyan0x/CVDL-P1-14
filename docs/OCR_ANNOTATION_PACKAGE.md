# V4 OCR annotation package

## Evidence and scope

**Observed implementation/source artifact:** prepared from immutable detector
commit `639c59b` (full SHA in `preparation_audit.json`), specifically
`docs/OCR_CODY_HANDOFF.md` §§What to find in the repo / Recommended work sequence,
and `evaluation/object_detection/01760a841333/runs/v4-reviewed-01/ocr_handoff/`
`README.md`, `manifest.json` and `transcriptions_template.csv`.
The package is validation-only (`valid`), for OCR diagnostics and setting
selection. The detector's held-out test is not included or opened for tuning.

**Project decision:** the review and scoring conventions below implement the
user's request to prepare annotation before scoring. They are not assessment
requirements. Required rubric fields/weights remain **not stated** in the
available brief material. Service identifier, route/road text and destination
remain distinct. Route labels are retained for review, without asserting that
the current checked-out app or coursework requires road-name recognition.

## Open the workspace

Start in [the prepared workspace](../evaluation/ocr_annotations/v4-reviewed-01/).

| File | Purpose |
| --- | --- |
| `annotation_review.csv` | 157 annotation-box text crops, in original template order |
| `prediction_review.csv` | 114 predicted text crops, independently pending |
| `image_review.csv` | All 53 images, including ten source zero-box negatives |
| `source/` | Byte-preserved source README, manifest, template and 381 PNG crops; panel crops are context |
| `preparation_audit.json` | Pinned Git provenance, input hashes, crop checks, counts and initial review state |

The original dataset paths in `source/manifest.json` describe the producer's
Windows machine. They are provenance, not usable local source-image paths.
Crop links in the working CSVs resolve against `source/`. Source image hashes
are copied from the manifest, not independently verified against absent originals.
Crop hashes are calculated from the supplied files. PNG signature and dimensions
are checked against boxes; full pixel decoding and human content review are
separate checks. No OCR engine was run and no text was supplied by preparation.

To reproduce into a **new** output directory from the repository root:

```sh
python3 scripts/prepare_ocr_annotations.py --ref 639c59b --output evaluation/ocr_annotations/v4-reviewed-02
```

This reads the Git snapshot without switching/merging branches or changing the
application detector. Existing output directories are refused. Keep `source/`
and the initial audit immutable. Save later review exports under new filenames;
never regenerate over completed annotations. Preserve real newlines in quoted
CSV transcription cells. Import identifiers and transcription as text in any
spreadsheet editor to avoid conversion of leading zeros or service identifiers.

## Retained and added columns

The first five columns are the original template columns: `crop`, `image`,
`label`, `transcription`, `review_status`. Annotation rows preserve their values
and order. Prediction rows use the same structure with blank transcription and
`pending` status; the handoff did not contain prediction transcription rows.

| Columns | Meaning / review action |
| --- | --- |
| `crop`, `image`, `label` | Immutable crop path, source image filename and supplied class; do not silently relabel |
| `transcription`, `review_status` | Visible text and explicit review lifecycle described below |
| `crop_source`, `image_id`, `split`, `class_id`, `annotation_id` | Manifest identity; prediction annotation ID stays empty |
| `source_image_sha256`, `source_width`, `source_height` | Source manifest provenance; not a claim that source images are locally available |
| `box_xyxy` | Original manifest box in source-image pixels, `[x1,y1,x2,y2]`, exclusive bottom/right |
| `crop_sha256`, `crop_width`, `crop_height` | Supplied crop identity and size; no padding/resizing applied |
| `detector_confidence` | Original prediction confidence only; empty for annotation boxes |
| `matched_gt_annotation_id_at_iou50`, `best_same_class_iou`, `candidate_gt_crop` | Diagnostic geometry candidate; never automatic text truth |
| `correspondence_status` | Predictions: `pending`, `same_visible_text`, `different_visible_text`, `no_match`, or `needs_resolution`; blank for annotation rows |
| `group_id`, `group_review_status` | Human-reviewed original/burst group and `pending`, `reviewed` or `needs_resolution`; initially blank/pending, not inferred from filename/hash alone |
| `field_status` | `present`, `blank`, `absent`, `wrong_field`; blank until reviewed |
| `legibility` | `full`, `partial`, `illegible`, or `not_applicable`; blank until reviewed |
| `reviewer`, `reviewed_at` | Actual reviewer and ISO date/time; never auto-filled as human attestation |
| `second_reviewer`, `second_reviewed_at` | Independent resolution/review for uncertain text or field/correspondence decisions |
| `exclusion_reason`, `notes` | Explicit reason for exclusion, ambiguity, clipping, quality and other context |

`group_id` is not a source-image ID: related images may share a group. Establish
groups across other splits before claiming independence. Nothing in this
preparation proves absence of training overlap or near-duplicate scenes.
Retain `valid` exactly; the image-level evaluator's `val` vocabulary is a
separate schema requiring an explicit conversion step.

## Human review procedure

Numbered [human review batches](../evaluation/ocr_annotations/v4-reviewed-01/human_review/README.md)
provide 18 annotation sheets (`A001`–`A157`) and 13 prediction sheets
(`P001`–`P114`), with up to nine crops per sheet. Their submission templates
retain every original working-row value and append neutral IDs/sheet names;
all transcription and reviewer fields remain blank. Copy a template to a new
reviewer-named export before entering human labels. Generate a new set with
`python3 scripts/prepare_ocr_human_review.py --output /path/to/new-review-directory`.
This requires Pillow and refuses existing output or already-labelled input.

1. Open the crop at its native size and, if useful, nearest-neighbour enlargement.
   Use panel context crops from the same source image to check field identity.
   Request the original image when necessary; do not guess missing context.
2. Apply [the transcription conventions](OCR_TRANSCRIPTION_RULES.md#transcription-conventions):
   Unicode NFC, visible case/punctuation/abbreviations, one word space, real
   line breaks, top-to-bottom order. The alphabet is open to reliably readable
   displayed characters; no digit-only or English-uppercase restriction is inferred.
3. Classify field status and legibility before entering text. Never reconstruct
   from filenames, route CSV endpoints, another frame or OCR suggestions.
4. Record reviewer/date, related-frame group and exclusions. Unresolved cases
   use `needs_resolution`; independent review records the second reviewer/date.
5. Review predicted crops independently. Compare any geometry candidate for
   clipping, extra text and wrong fields. Even `same_visible_text` requires human
   inspection; it does not automatically populate the transcription. A prediction
   with no candidate can still contain readable text: transcribe what is visible
   and use `no_match`, retaining the unmatched-prediction category for evaluation.
6. Review all image-register entries, including source zero-box negatives. Source
   zero-box status is an annotation fact, not a new human judgement that no EDS
   exists. Keep uncertain negative cases pending or `needs_resolution`.

Review lifecycle: `pending` → `reviewed` when the row is resolved and reviewer/date
are real; `needs_resolution` while disputed; `excluded` for documented invalid
crops, missing context or deliberate exclusions. An unreadable crop can be
`reviewed` with `legibility=illegible`: review and readability are different facts.
Excluded rows retain their provenance and require `exclusion_reason` and review
metadata. `wrong_field` requires exclusion or resolution in a new version, not
silent class mutation. No automatic eligibility is implied by typing `reviewed`.

## Text states and scoring policy

These rules specify the later crop scorer; no accuracy has been measured and
the existing application evaluator does not consume these CSVs.

| Reviewed state | Stored values | Scoring |
| --- | --- | --- |
| Complete readable text | `present`, `full`, nonempty transcription without `[UNK]` | Eligible for primary raw exact match/CER once review and grouping checks pass |
| Partial or clipped | `present`, `partial`, readable text plus `[UNK]` for each unresolved span | Separate challenge set; exclude from whole-field exact/CER; no guessed completion |
| Fully unreadable | `present`, `illegible`, exactly `[UNK]` | Exclude from textual accuracy; retain for abstention/error analysis |
| Visible intended field, no text | `blank`, `not_applicable`, empty transcription | Separate blank-field exact-empty rate and hallucination count; exclude from primary text accuracy/CER |
| Intended field not present | `absent`, `not_applicable`, empty transcription | No text target; exclude from CER/text accuracy; count output as false field detection only after source-level/geometry review |
| Unreviewed or unresolved | `pending`/`needs_resolution`, unknown cells remain empty | No scoring; counts must be reported |
| Wrong field or invalid crop | `wrong_field` or documented invalidity, `excluded`, explicit reason | Exclude from recognition accuracy; retain detector/annotation error category |

Blank means the region exists but is empty; absent means the field itself does
not exist. If crop-only evidence cannot distinguish them, leave it unresolved.
Do not manufacture absent crops for negative images or missing detector outputs.
Do not store a literal `null` or `""` as a transcription. The combination of
status, legibility and human review distinguishes a reviewed empty value from
the same empty CSV cell in a pending row.

Primary eligibility requires `review_status=reviewed`, real reviewer/date,
`field_status=present`, `legibility=full`, nonempty NFC transcription without
`[UNK]`, no exclusion reason, and `group_review_status=reviewed` with nonempty
`group_id`. Predictions additionally need resolved correspondence review.
Validate these combinations before scoring. Report eligible/total and each
excluded state separately by field and crop source.

Raw exact match/CER preserves case, punctuation and newlines; apply NFC and the
declared per-line word-space convention consistently to truth and predictions.
For an optional separately labelled normalized score, apply NFC, Unicode
`casefold()` and collapse all whitespace (including line breaks) to a single
ASCII space, trimming ends. Do not expand abbreviations or remove punctuation.
Micro CER is total edit distance divided by total eligible reference characters;
count spaces/newlines in raw CER. Exact accuracy is correct eligible fields /
eligible fields. An overall result is count-weighted, not an unweighted average
of field percentages. Empty/error predictions from an available engine remain
in the denominator; unavailable engines are reported as unavailable, not ranked.

For blank cases, exact-empty uses the same declared whitespace/NFC processing:
an empty result succeeds; any nonempty text is a hallucination. Do not divide by
zero reference characters to compute blank CER. Partial spans need a separately
reviewed alignment protocol before any span score. `[UNK]` is annotation syntax,
never literal training truth or OCR target text.

Crop-only results are conditional on available crops. Keep unmatched predictions,
missing detections and image negatives visible in counts; do not describe crop
accuracy as end-to-end accuracy. The ten zero-box images are in `image_review.csv`,
not represented by fabricated empty text rows. Raw OCR and reference-matched
output must remain separate, as must detector confidence, OCR confidence and
reference similarity.

## What is still required

Human text/field review, group/overlap audit, full source images where needed,
and all OCR measurements remain outstanding. For application evaluation,
prepare a separate reviewed image-level JSON under
`backend/app/evaluation/MANIFEST_FORMAT.md`, with real screen boxes and review
attestation. Map absent/unreadable fields to `null` (excluded text), reviewed blank
to an empty string, and reviewed negatives to empty displays only after image
review. That evaluator scores number/destination; route-text evaluation needs
explicit implementation. Do not convert pending rows to reviewed JSON.
