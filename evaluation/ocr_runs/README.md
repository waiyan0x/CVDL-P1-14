# OCR raw-inference runs

- [Run 01](easyocr-v4-mps-baseline-01/README.md): exploratory `row_projection_v1`.
  Visual QA found LED dot rows incorrectly treated as text lines. Preserve as
  historical implementation evidence; do not use as a validated layout baseline.
- [Run 02](easyocr-v4-mps-baseline-02/README.md): historical automatic raw diagnostic,
  `row_projection_v2`, actual Apple M1 recognizer device `mps:0`. All 271 attempts
  completed; line segmentation remains unverified and still misses some skewed
  or clipped multiline layouts. No OCR accuracy is calculated.
- [Fixed lines 01](easyocr-v4-mps-fixed-lines-01/README.md): first run using the
  frozen AI-reviewed line regions; 251 completed, 20 explicit unresolved layouts.
- [Fixed lines 02](easyocr-v4-mps-fixed-lines-02/README.md): verifies the extended
  runner's EasyOCR path; identical raw text/status/geometry to fixed lines 01.
- [TrOCR failed attempt](trocr-base-printed-v4-mps-fixed-lines-01/README.md):
  public checkpoint reached MPS, but disk exhaustion prevented inference.
  No predictions or benchmark timings exist for this attempt.

See [model selection status and portable next steps](../../docs/OCR_MODEL_SELECTION.md).

See [the protocol and known limitations](../../docs/OCR_CROP_BASELINE.md).
Do not overwrite runs. Both preserve exact runner/core source snapshots and
environment/input/model evidence. Timing differences between runs are not an
accuracy ranking or a controlled performance comparison.
