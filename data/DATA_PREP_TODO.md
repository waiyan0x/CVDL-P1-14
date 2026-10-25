# Data Prep: next work and remaining tasks

This checklist combines the Project & Data Preparation allocation with what is
visible in the `data-preparation` branch. An unchecked item means completion is
not evidenced here; it may already be in progress outside Git. Dataset counts
and image types are recorded in [IMAGE_CATEGORIES.md](IMAGE_CATEGORIES.md).

## Current recovery status (25 October 2026)

- [x] Recheck the accepted 199-image export and visually confirm its three
  cross-split overlaps; record checksum-bound training exclusions.
- [x] Create a separate clean export (137/39/20) with validation/test unchanged
  and no remaining cross-split dHash matches at distance <= 4.
- [x] Record the four active classes and their explicit training mapping.
- [x] Inspect the 22 zero-box images in a contact sheet with selected full-size
  checks; retain them as existing accepted examples. Platform Null history and
  full positive-box semantic review remain unverified.

Use the [current training handoff](../docs/data_preparation/TRAINING_READINESS.md).
The historical checklist below describes wider work, including source provenance
and grouping by recording, beyond the repaired scene overlaps.

## Next work (do first)

- [x] **Record the bbox annotation contract.** The [guide](../docs/annotation/guide.md)
  includes front/side EDS, excludes rear EDS and defines four classes and multiple
  displays per frame. Reviewing all current labels against it remains open.
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
- [x] Record the [phase sequence and augmentation recipe](../docs/data_preparation/README.md)
  and implement training-only augmentation with unchanged validation/test copies.
- [ ] Review the resulting small-text readability and resolve flagged similar
  scenes across current splits before training. Visual plots are available in
  [the inspection notebook](../notebooks/data_visual_checks.ipynb).

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
