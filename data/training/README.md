# Final datasets for model training

The current detector dataset is `2026-10-24-eds-v1/`:

```text
data/training/2026-10-24-eds-v1/
  train/                       # 137 clean originals + 274 augmented images = 411
    _annotations.coco.json     # Labels for all 411 training images
  valid/                       # 39 unchanged original images and COCO JSON
  test/                        # 20 unchanged original images and COCO JSON
  augmentation_manifest.json  # Source hashes, transform provenance, output checksums
```

Point detector training, validation and evaluation at these three splits.
`src/data_preparation/config.py::TRAINING_DATASET` selects this version, and
`load_coco_splits()` loads it by default. There are no model training scripts yet;
future trainers should use this configured path. Keep validation and test separate
from the images used to fit the model.

`data/labelled/` holds accepted annotation sources before augmentation. The
cleaned source for this dataset is `data/labelled/2026-10-24-clean-v1/`.
`data/processed/` contains historical exports. The final verified export formerly
at `data/processed/2026-10-24/eds-torch-v2-clean-v1/` was relocated here without
changing its images, labels or augmentation manifest.

Build or verify the current version with:

```powershell
python scripts/03_augment_dataset.py
python scripts/03_augment_dataset.py --write
```

Both commands use the cleaned labelled source. The first validates the cleaned labelled source without
writing; the second verifies an existing export or builds a missing one.
Changed inputs/settings require a new version via `--output data/training/<version>`.

The four-class mapping, readiness checks and remaining limits are in the
[training handoff](../../docs/data_preparation/TRAINING_READINESS.md).
Coordinate any further trainer augmentation with this offline recipe. OCR
training still requires verified text transcriptions.

Version folders are local and ignored by Git. This README is tracked.
