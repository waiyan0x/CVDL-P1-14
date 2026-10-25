# Data Prep: next work and remaining tasks

This checklist combines the Project & Data Preparation allocation with what is
visible in the `data-preparation` branch. An unchecked item means completion is
not evidenced here; it may already be in progress outside Git. Dataset counts
and image types are recorded in [IMAGE_CATEGORIES.md](IMAGE_CATEGORIES.md).

## Next work (do first)

- [ ] **Confirm the dataset contract.** Decide which front, side, and rear EDS
  formats are supported, which text fields must be extracted, and whether
  multiple EDS in one frame are in scope. Record camera and uploaded-video
  requirements and consistent EDS box, text-line, and field-label rules.
- [ ] **Make the current snapshot retrievable and traceable.** Share the raw,
  labelled, and processed files at the paths in `manifests/2026-10-24.csv`.
  Record the source, collection method, usage permission, and source group for
  each image or recording. The current manifest contains paths, sizes, and
  checksums, but no provenance.
- [ ] **Audit the existing labels and split groups.** The raw manifest has
  **12 exact-duplicate groups (13 extra files)**. Find near-duplicates and
  related frames, then check that each source group stays in one split. Review
  EDS box boundaries, missing boxes, and the **22 base-export images with no
  boxes**; classify these as intentional negatives or annotation omissions.

## Other Data Prep TODOs

### Acquisition and cleaning

- [ ] Collect representative camera recordings and uploaded-video examples.
- [ ] Check coverage of EDS formats, distance, angle, lighting, blur,
  obstruction, multiple buses, and scenes without a front EDS against the
  supported scope; collect examples for gaps.
- [ ] Check for corrupt or unsuitable files and record decisions on exclusions
  and duplicate or near-duplicate groups.

### Annotation and OCR ground truth

- [ ] Complete and review EDS boxes using the agreed rules, including all
  in-scope displays and hard negative scenes.
- [ ] Create EDS crops with verified raw-text transcriptions and, where needed,
  text-line or field labels. Mark unreadable, partial, and special messages
  consistently.

### Splits, augmentation, and robustness

- [ ] Confirm train, validation, and held-out test membership after grouping
  duplicates, related frames, and recordings by source. Preserve the held-out
  test set for final evaluation.
- [ ] Record preprocessing and augmentation settings and apply training
  augmentations only to training images. Keep separate robustness conditions
  for blur, lighting, and perspective without changing the original test set.

### Reference data and versioning

- [ ] Obtain the reference CSV; record its source, fields, version, and intended
  use. Check missing records, inconsistent formatting, and coverage gaps.
- [ ] Version raw inputs, labels, OCR ground truth, splits, derived exports, and
  reference files together so later experiments can reproduce a snapshot.

### Project decisions needed for handoff

- [ ] Define expected outputs, update interval, failure behaviour, and timing
  requirements for camera and uploaded-video use.
- [ ] Document the detection → crop → OCR → reference matching → display
  pipeline, target hardware, model candidates, evaluation metrics, and a fair
  model-comparison protocol.
