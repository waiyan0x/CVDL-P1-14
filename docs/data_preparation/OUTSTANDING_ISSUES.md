# Pipeline review — 25 October 2026

The review covers the data-preparation code and current detector-training
handoff. The final dataset remains `data/training/2026-10-24-eds-v1/` with
411 training, 39 validation and 20 test images. These fixes preserve its files.

## Resolved

| Issue | Resulting behaviour | Regression coverage |
| --- | --- | --- |
| Normalization included augmented training rows and accepted held-out splits | The loader tags original/augmented provenance; statistics use original training rows only and reject validation/test | Original and augmented-export statistics agree; held-out splits rejected |
| Model loading did not verify frozen export checksums | Existing export manifests are checked before image loading; the configured model dataset requires a manifest | A changed but decodable image fails loading; incomplete augmentation provenance is rejected |
| An exact train/held-out duplicate stopped the audit before exclusions could run | The audit can inspect exact overlaps and apply reviewed training exclusions; normal loading remains strict | An exact duplicate fails normal loading, then audits and cleans successfully |
| Excluded annotations remained in the cleanup preflight | Image rows, COCO images and annotations are filtered together before auditing | A legacy class used only by an excluded image no longer blocks its removal |
| Newly generated augmentations were not checked for cross-split similarity | A similar scene introduced by augmentation prevents the staged export from being published | Publication fails and leaves no output dataset |

Verification of the real dataset confirmed all 473 output checksums and zero
cross-split similarity matches,
unchanged validation/test, an unchanged idempotent export, and identical
normalization statistics from the final dataset's 137 originals and the clean
source. The visual notebook also executes all 12 plots without embedding outputs
in the tracked source.

The new checks supplement the existing source hashes, atomic output staging,
box geometry validation, unchanged holdouts and rejection of modified exports.
`tests/test_data_preparation.py`, `tests/test_readiness.py` and
`tests/test_readiness_cli.py` contain the regressions; the full suite has 31 tests.

## Open work requiring additional evidence

- **Capture provenance and source permissions:** recording/capture IDs and
  source records are missing. Similarity checks do not prove that all frames
  from each recording are confined to one split. Populate verified source
  groups before making a stronger evaluation-independence claim.
- **Complete label review:** accepted labels exist, but this run does not
  establish that every positive box includes all eligible side panels or
  correctly distinguishes route and destination. Review against the annotation
  guide; zero-box platform Null history is also unavailable.
- **OCR ground truth:** verified text transcriptions are absent. Detector COCO
  boxes alone cannot support supervised OCR fine-tuning.
- **Model integration:** no model trainer is implemented or selected. Its
  input size, normalization and foreground/background label convention must be
  configured for that model. The four-class COCO mapping remains explicit in
  the [training handoff](TRAINING_READINESS.md).
- **Reproducible distribution:** payloads are local and shared storage is not
  configured. Git contains code and notebook metadata; another machine still needs the
  exact dataset files. The reference CSV is also not supplied.
- **Later coverage and evaluation:** collect representative camera/uploaded-video
  examples and fill coverage gaps when evaluating generalization. Check small-text
  readability at the chosen model input size, and define runtime hardware,
  update/failure behaviour, evaluation metrics and a model-comparison protocol.

These are open requirements, not failed code checks, and must not be marked
complete by inventing provenance, labels, permissions or model measurements.
The current image export is prepared for a detector-training baseline. The items
above cover stronger evidence and later project stages; they do not require
rebuilding the already verified export before starting that baseline.
