# Standalone preparation scripts

Run these commands from the repository root after installing `requirements.txt`.
All stages are independent; notebooks are optional visual inspection only.

```powershell
python scripts/01_prepare_and_split.py
python scripts/02_auto_annotate.py
python scripts/03_augment_dataset.py
```

These defaults inspect/plan/validate without writing datasets or loading a model.
Use each script's `--help` to change paths, cutoff and seed.

| Stage | Explicit action | Result |
| --- | --- | --- |
| Split | `python scripts/01_prepare_and_split.py --write --output data/raw/2026-10-24/splits/new-v1` | Frozen image copies and manifest; do this before annotation |
| Annotation | `python scripts/02_auto_annotate.py --run --limit 3 --output experiments/eds_autodistill/outputs/trial-001` | Isolated draft COCO, overlays and review queue |
| Augmentation | `python scripts/03_augment_dataset.py --write` | New `data/processed/2026-10-24/eds-torch-v2/` containing originals and training variants |

The current split directory is `data/raw/2026-10-24/splits`; do not replace it.
Pass `--input` to annotation if you prepared a different snapshot. Annotation uses
three images per split by default; `--limit 0` selects all. Review the trial first.
Copy accepted labels manually to `data/labelled/<cutoff>/` before augmentation.

For reviewed Null examples, annotation accepts `--negatives paths.json`: a JSON
list of exact input-relative paths such as `train/example.jpg`. A missing model
prediction does not establish that an image is a negative.

See [phase context and augmentation recipe](../docs/data_preparation/README.md).
