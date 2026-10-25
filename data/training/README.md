# Final datasets for model training

The current detector dataset is `2026-10-24/`, matching the raw and labelled
batch folder names:

```text
data/training/2026-10-24/
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

`data/labelled/2026-10-24/` holds the accepted original images and annotations
before augmentation (137 train, 39 validation, 20 test). The former cleaned
export now occupies this canonical path; the older export was removed.
Only `2026-10-24/`, built with torchvision, is retained as an augmented
training export. `data/processed/` and its obsolete `eds-aug-v1` and
`eds-torch-v1` exports have been removed. Raw and labelled sources remain so the
current export can still be audited and reproduced.

Build or verify the current version with:

```powershell
python scripts/03_augment_dataset.py
python scripts/03_augment_dataset.py --write
```

Both commands use the accepted labelled source. The first validates the source
without writing; the second verifies an existing export or builds a missing one.
Changed inputs/settings require a new version via `--output data/training/<version>`.

The four-class mapping, readiness checks and remaining limits are in the
[training handoff](../../docs/data_preparation/TRAINING_READINESS.md).
Coordinate any further trainer augmentation with this offline recipe. OCR
training still requires verified text transcriptions.

Version folders are local and ignored by Git. This README is tracked.

Loading verifies the frozen output checksums and augmentation provenance.
For optional dataset normalization, `fit_training_statistics(splits["train"])`
uses only the 137 original training images even when loading the full 411-image
training split. It rejects validation/test inputs. See the
[pipeline review](../../docs/data_preparation/OUTSTANDING_ISSUES.md) for resolved
code gaps and remaining data requirements.
