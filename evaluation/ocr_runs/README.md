# OCR raw-inference runs

- [Run 01](easyocr-v4-mps-baseline-01/README.md): exploratory `row_projection_v1`.
  Visual QA found LED dot rows incorrectly treated as text lines. Preserve as
  historical implementation evidence; do not use as a validated layout baseline.
- [Run 02](easyocr-v4-mps-baseline-02/README.md): current raw diagnostic,
  `row_projection_v2`, actual Apple M1 recognizer device `mps:0`. All 271 attempts
  completed; line segmentation remains unverified and still misses some skewed
  or clipped multiline layouts. No OCR accuracy is calculated.

See [the protocol and known limitations](../../docs/OCR_CROP_BASELINE.md).
Do not overwrite runs. Both preserve exact runner/core source snapshots and
environment/input/model evidence. Timing differences between runs are not an
accuracy ranking or a controlled performance comparison.
