# Reviewed OCR benchmark manifest

Run the application, then run:

```sh
.venv/bin/python scripts/evaluate.py --manifest /absolute/path/to/reviewed.json
```

The CLI compares YOLO + EasyOCR, Tesseract and TrOCR through `/api/comparisons`.
Each image is detected once and identical crops are shared. Default one warmup
comparison is excluded from timing. Use a dedicated idle server for measurements.

Start with `manifest.example.json`; it deliberately contains no invented truth
and cannot run until reviewed images and review details are provided. Required
fields are `schema_version: 1`, `dataset` with nonempty `id`, `version`, `split`
(`val`, `test` or `held_out`), `review` with `reviewed: true`, a real `reviewer`
and ISO `reviewed_at`, and a nonempty `images` array.

Each image requires a unique `id`, `path` relative to the manifest (or absolute),
its exact lowercase `sha256`, and `displays`. Each display requires a locally
unique `id`, a reviewed whole-screen pixel `box: [x1,y1,x2,y2]`, `bus_number`,
and `destination`. Transcribe exactly what is visible, including line breaks.
Coordinates refer to the upright image after EXIF orientation. A field value
may be `null` to exclude it from scoring; at least one field per display must
have reviewed text. Use an empty `displays` array for a reviewed negative image.
An empty text string means reviewed empty text, not unknown/unreadable text.

Known exact training overlaps and repeated images are excluded by default and
listed in the report. `--include-overlap` explicitly marks a non-independent
run. Hash filtering does not establish absence of related scenes, OCR training
overlap or near-duplicates; reviewers must establish these independently.

The report records the manifest hash, review attestation, image/model hashes,
dataset audit, settings, versions, hardware, warmup, engine errors, exact and
case/whitespace-normalized field accuracy and character error rate, complete
reviewed-field accuracy, median/p95 server timing and comparison roundtrip.
Initially available engines' failed frames count as empty predictions;
unavailable engines are unscored. Different OCR confidence scores are never
used as correctness or cross-model rankings. EDS precision/recall uses only
direct model screens at IoU 0.5; inferred envelopes are excluded. Detector mAP
and reference-endpoint correctness are not computed by this text benchmark.

Reports are written atomically to `evaluation/reports/` by default and discovered
by `/api/evaluation`. Reviewed transcriptions are a human attestation, not
automatic proof of annotation correctness. Keep original manifests and datasets
alongside published reports for reproducibility.
