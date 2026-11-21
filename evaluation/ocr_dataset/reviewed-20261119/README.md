# Reviewed OCR text-label handoff — 19 November 2026

This is the crop-to-text reference dataset, not Brendan's image/box dataset and
not OCR predictions. `text` is the reference transcription used by the benchmark.
Use the same references for pretrained and fine-tuned models.

- `labels.csv`: all 776 benchmark rows: train 387, validation 271, test 118.
- `evaluation_labels.csv`: the 175 eligible held-out rows only: validation 130
  (79 annotation, 51 detector crops), test 45 annotation crops.
- Train: 384 currently scorable rows, diagnostic only; primarily AI labels.
  `original_training_text` preserves the labels actually used for training;
  `text` includes the benchmark's four recorded human spot-check overrides.
  This export does not retrain models or change their training labels.
- Human-confirmed validation/test readings include manual corrections. Review
  provenance is retained; an AI label is not promoted to human ground truth.
- Unreadable/partial, wrong-field, challenge and train-overlap rows remain in
  `labels.csv` with exclusion reasons; they have not been silently discarded.

Read CSVs with a CSV parser: `text` can contain quoted real line breaks. Preserve
case, punctuation, abbreviations and `[UNK]`; do not infer text from route data.
Scoring uses NFC, casefold, NFC and collapsed whitespace; punctuation remains.
Failed/missing predictions count as empty. Train scores are diagnostic only.
TEST is not for training or threshold tuning; prior model selection used TEST,
so it is not an independent final estimate. Synthetic images are not included.

`review_id` identifies the crop. `crop` preserves its benchmark source path;
it is not a path relative to this text-only package. For validation/test,
`matching_record_id` joins to the selected-model matching handoff, and
`matching_crop` locates its image inside that package. Crop SHA-256 values were
verified against all 389 packaged validation/test images. No train images are
included and train pixels were not re-verified by this export.

Matching handoff: `.runtime/ocr-matching-final-20261119.zip` (separate package).
It contains raw/normalised selected-model OCR, separate validation/test labels,
route reference, weights, crop/source images, inference code and an ownership
review form. Display ownership remains a geometry proposal until human review;
text-label review does not establish that fields belong to the same bus.

See `manifest.json` for source hashes, exact counts and file hashes. This export
is derived from the benchmark's frozen labels; it is not a new human review.
