# V4 OCR review workspace

Status: unreviewed preparation; no OCR truth or accuracy is asserted.

Read repository-root `docs/OCR_ANNOTATION_PACKAGE.md` and `docs/OCR_TRANSCRIPTION_RULES.md` before review.

- `annotation_review.csv`: supplied annotation text-crop template plus metadata.
- `prediction_review.csv`: independent predicted text-crop review.
- `image_review.csv`: all source images, including source zero-box negatives.
- `source/`: unchanged Git snapshot; CSV crop paths are relative to this directory.
- `preparation_audit.json`: immutable initial provenance, hashes and counts.

Preserve source files and the initial audit. Save review exports under new names. Do not infer text from filenames, route references or diagnostic IoU matches.
