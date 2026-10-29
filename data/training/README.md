# Final datasets for model training

## Current local inventory

Verified on **2026-10-29** by counting image files and matching them one-to-one
with the COCO `images` records. All referenced images exist and their dimensions
match their annotations; no extra image files were found in these splits.

| Split | Images | Annotations |
| --- | ---: | ---: |
| Train | 420 | 1,674 |
| Validation | 39 | 154 |
| Test | 20 | 83 |
| **Total** | **479** | **1,911** |

```text
data/training/2026-10-24/
  train/                       # 420 images
    _annotations.coco.json     # 420 image records, 1,674 annotations
  valid/                       # 39 images and COCO JSON
  test/                        # 20 images and COCO JSON
```

The current COCO files identify this as a **Roboflow version 2 export**. Training
metadata groups the 420 outputs under 140 source names, each with three outputs.
This establishes grouping, not which output is the original or the exact
transforms applied. The previous **137 originals + 274 augmentations = 411**
description does not describe the current training folder.

The separate accepted labelled source, `data/labelled/2026-10-24/`, still contains
**196 images: 137 train, 39 validation (`val/`), 20 test**. Do not equate its
137 training originals with the current export's 140 source-name groups or
assume validation/test files are byte-identical to the labelled source.

## Loading and reproduction

`src/data_preparation/config.py::TRAINING_DATASET` selects this version.
Keep train, validation and test separate during fitting and evaluation.
The current local folder has **no `augmentation_manifest.json`**. The loader
`load_coco_splits()` requires an export manifest for the configured training
dataset and will reject this folder until its provenance/integrity requirements
are addressed. Counts above verify inventory, not training readiness.

The repository's torchvision recipe uses brightness ±10%, rotation ±3°,
salt/pepper noise at a 1% expected pixel rate, and Gaussian blur sigma 0–1 px.
Its default multiplier is three. That recipe is not proof of how the current
Roboflow export was produced. [Representative samples](../samples/README.md)
include one isolated demonstration per effect.

```powershell
python scripts/03_augment_dataset.py
python scripts/03_augment_dataset.py --output data/training/<new-version> --write
```

The first validates the accepted labelled source without writing. For a new
torchvision export, choose a new version folder; `--write` at the current default
path refuses an existing folder without its expected manifest. Do not overwrite
the current dataset or fabricate a manifest from counts alone. Normalization
helpers also require verified original/variant provenance.

The [training handoff](../../docs/data_preparation/TRAINING_READINESS.md) and
[pipeline review](../../docs/data_preparation/OUTSTANDING_ISSUES.md) contain
earlier preparation context; their old 411/470 counts and manifest assertions
are historical and do not certify this local Roboflow snapshot. OCR training
still requires verified text transcriptions. Version folders stay local;
this README is tracked. See [the inventory](../samples/dataset_inventory.json)
for annotation hashes and verified counts.
