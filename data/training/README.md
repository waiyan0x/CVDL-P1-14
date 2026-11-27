# Final datasets for model training

## New Roboflow v4 export (local, review required)

The corrected version is now `data/training/2026-11-05-roboflow-v4-reviewed/`.
It has a verified `preparation_manifest.json` and passed the automated audit:
735 train, 53 validation and 53 test images, with no flagged cross-split similar
pairs or marked-up images. Nine training variants from three overlapping source
families were excluded; the source export and held-out images were preserved.
The current detector run `v4-reviewed-01` used this corrected version. See its
[training, validation and final-test results](../../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md).
Human review of all four class semantics, negatives and source/capture records
remains necessary. Both local dataset folders are ignored by Git.

The supplied `Front EDS.v4i.coco` export was copied without modifying its files to
`data/training/2026-11-05-roboflow-v4/` on 2026-11-05. Its 855 files (142.2 MiB)
were SHA-256 compared with the supplied folder; all copies matched. The export
contains 744 train, 53 validation and 53 test images, with 2,784 / 221 / 171
boxes and 147 / 10 / 12 zero-box images. It retains the four active EDS classes
and an unused zero-box parent category.

The automated audit passed structural checks but **did not pass readiness**:
it flagged six similar-scene train/validation or train/test pairs and three
`annotated_` training images with drawn-on boxes. The full local report is
`.runtime/front-eds-v4-source-audit.json`. Review those cases, source/capture
groups and zero-box semantics with Jy before preparing a new benchmark. This
Roboflow export has no project integrity/augmentation manifest and cannot be
loaded by the strict detector training script as-is. Do not invent a manifest
or use its validation/test splits to choose changes without resolving overlap.

The v4 payload is ignored by Git under the repository's dataset policy; a branch
pull does not download it. The previous `2026-10-30-torchvision` benchmark input
and `baseline-01` results remain unchanged. Source metadata in the export states
Roboflow Front EDS v4, exported 2026-11-05, with a CC BY 4.0 notice; the individual
image source and capture/permission register still need review.

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
