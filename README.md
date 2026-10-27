# Bus EDS data preparation

Prepare local bus images for front/side electronic destination sign detection.
Standalone Python scripts own processing; the single notebook only displays
augmentation comparisons and representative scene categories.

Model dataset: **`data/training/2026-10-24/`**.
Its `train/` contains 137 accepted originals + 274 augmented images (411 total);
`valid/` and `test/` contain 39 and 20 unchanged originals.
`data/labelled/` is the annotation source before augmentation. Only the current
torchvision training export is retained; superseded exports have been removed.
See the [training dataset](data/training/README.md) and
[readiness handoff](docs/data_preparation/TRAINING_READINESS.md).

## Commands for a new batch

Run from the repository root (the folder containing `scripts/`, `src/` and
`requirements.txt`). The example below processes a separate `2026-10-31` batch;
replace that date consistently for another batch. The configured defaults still
point to `2026-10-24`, so keep the new batch arguments explicit.

```powershell
python -m pip install -r requirements.txt

# 1. Put the new raw images in data/raw/2026-10-31/, then freeze their splits.
python scripts/01_prepare_and_split.py --cutoff 2026-10-31 --output "data/raw/2026-10-31/splits" --write

# 2. Annotate all images and open the local review editor after inference.
python scripts/02_auto_annotate.py --cutoff 2026-10-31 --input "data/raw/2026-10-31/splits" --output "experiments/eds_autodistill/outputs/2026-10-31-run-001" --limit 0 --run --review
```

In the editor, correct the boxes/classes and save **Accept positive** or
**Confirm negative** for every image. Progress is saved in the experiment's
`review_decisions.json`. Viewing overlay PNGs alone does not record acceptance;
there is no need to send overlay paths to anyone. Automatic checks flag label
issues; visual confirmation of front/side EDS coverage and negatives is manual.

After every image is accepted, click **Export reviewed dataset** with destination
`data/labelled/2026-10-31`, or stop the editor with Ctrl+C and use the export
command below. Use one export method; an existing destination is not overwritten.

```powershell
# 3. Export saved decisions (skip if already exported through the editor).
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --export "data/labelled/2026-10-31"

# 4. Audit the accepted dataset. Resolve failures before continuing.
python scripts/00_audit_dataset.py --input "data/labelled/2026-10-31" --report ".runtime/labelled-audit-2026-10-31.json"

# 5. Run only after the audit reports automated_checks_passed: true.
python scripts/03_augment_dataset.py --cutoff 2026-10-31 --input "data/labelled/2026-10-31" --output "data/training/2026-10-31" --multiplier 3 --write
```

The final dataset is `data/training/2026-10-31/{train,valid,test}/`, with images and
`_annotations.coco.json` in each split. Training contains originals plus variants;
validation/test images and COCO JSON are copied unchanged. Separate batch paths
preserve the existing `2026-10-24` dataset; batches are not automatically merged.

To resume review without rerunning inference:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --serve
```

The experiment's `overlays/{train,val,test}/` folders contain `__draft.png` images
with explicit boxes/classes and `__raw.png` detector proposals. The editor shows
your current corrections; static overlays retain the initial predictions.

See [script arguments and defaults](scripts/README.md) for path overrides,
planning commands, and working with existing accepted labels. Without `--write`,
split/augmentation commands only plan/validate; annotation needs `--run` for
inference and defaults to three images per split unless `--limit 0` is supplied.
No model training is included.

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
local. Git contains code, documentation and notebook sample metadata. Notebook
outputs are cleared before committing so images are not embedded in Git.

```powershell
python -m unittest discover -s tests -v
```
