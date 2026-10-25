# Tracked dataset records

| File | Purpose |
| --- | --- |
| `2026-10-24.csv` | Original 898-file inventory: path, bytes and SHA-256. Historical paths include former `roboflow/` subdirectories. |
| `2026-10-24-preview-samples.json` | Three hand-reviewed examples per coverage category plus three original training images for augmentation plots. Current paths, hashes and observations. |

The category definitions live in [../IMAGE_CATEGORIES.md](../IMAGE_CATEGORIES.md),
not inside this directory. Coverage categories overlap and are separate from
the four object classes in COCO. The sample manifest is illustrative, not a
complete per-image classification or a count of category membership.

The notebook checks the recorded sample hashes before plotting. Restore the
expected local image if it is missing or changed; do not silently replace it.
Dataset exports also contain local split/augmentation manifests. Keep those
with their payload versions; source and output hashes must identify the run.

`2026-10-24-training-exclusions.json` records the three visually confirmed
training overlaps excluded from the separate clean export, with checksums for
each training image and its held-out counterpart. See the
[training handoff](../../docs/data_preparation/TRAINING_READINESS.md).

`2026-10-25-readiness.json` records the completed clean/processed verification,
including 20 passing tests, holdout preservation, source/output checksum checks,
and the exact training class mapping. This is a dataset check, not a model
accuracy result or proof of complete capture-group independence.
