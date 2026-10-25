# Bus EDS data preparation

Prepare local bus images for front/side electronic destination sign detection.
Standalone Python scripts own processing; the single notebook only displays
augmentation comparisons and representative scene categories.

Model dataset: **`data/training/2026-10-24-eds-v1/`**.
Its `train/` contains 137 clean originals + 274 augmented images (411 total);
`valid/` and `test/` contain 39 and 20 unchanged originals.
`data/labelled/` is the annotation source before augmentation; `data/processed/`
contains historical exports. See the [training dataset](data/training/README.md)
and [readiness handoff](docs/data_preparation/TRAINING_READINESS.md).

```powershell
python -m pip install -r requirements.txt
python scripts/01_prepare_and_split.py
python scripts/02_auto_annotate.py
python scripts/03_augment_dataset.py
```

The commands above plan or validate. Dataset writes require `--write` and model
inference requires `--run`. No model training is included.

| Location | Purpose |
| --- | --- |
| [scripts/](scripts/README.md) | Independent phase commands and flags |
| [docs/data_preparation/](docs/data_preparation/README.md) | Phase sequence, contracts and augmentation rationale |
| [src/data_preparation/](src/data_preparation/README.md) | Reusable loading, splitting, annotation, augmentation and preprocessing code |
| [notebooks/](notebooks/README.md) | Read-only before/after plots and three images per coverage category |
| [data/](data/README.md) | Local dataset layout, tracked manifests and coverage |
| [docs/annotation/](docs/annotation/README.md) | Autodistill annotation, isolated drafts and review |
| [Annotation guide](docs/annotation/guide.md) | Front/side EDS scope, four bbox classes, exclusions and review rules |

Inspect/group raw images -> freeze train/validation/test -> annotate and review ->
validate accepted COCO -> augment training only. Keep validation/test unchanged.
The existing snapshot is already split; do not replace its membership.

Images, labels, generated exports, model caches and virtual environments stay
local. Git contains code, documentation and checksum/sample manifests. Notebook
outputs are cleared before committing so images are not embedded in Git.

```powershell
python -m unittest discover -s tests -v
```
