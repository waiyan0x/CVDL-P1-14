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
| Augmentation | `python scripts/03_augment_dataset.py --write` | Final `data/training/2026-10-24-eds-v1/`: train originals + variants, unchanged validation/test |

The current split directory is `data/raw/2026-10-24/splits`; do not replace it.
Annotation runs through `02_auto_annotate.py`, alongside the other phase scripts;
its shared implementation is in `src/data_preparation/`. The experiment directory
stores local runtime files only. See the [annotation guide to running and reviewing
drafts](../docs/annotation/README.md).
Pass `--input` to annotation if you prepared a different snapshot. Annotation uses
three images per split by default; `--limit 0` selects all. Review the trial first.
Copy accepted labels manually to `data/labelled/<cutoff>/` before augmentation.

For reviewed Null examples, annotation accepts `--negatives paths.json`: a JSON
list of exact input-relative paths such as `train/example.jpg`. A missing model
prediction does not establish that an image is a negative.

See [phase context and augmentation recipe](../docs/data_preparation/README.md).

## Audit and clean the current accepted export

```powershell
python scripts/00_audit_dataset.py
python scripts/00_audit_dataset.py --write --report .runtime/clean-label-audit.json
python scripts/03_augment_dataset.py --write
```

The audit returns exit code 1 when automated readiness checks fail. Cleaning uses
three checksum-bound, visually reviewed training exclusions from
`data/manifests/2026-10-24-training-exclusions.json`; it creates a separate export,
keeps validation/test bytes and accepted originals, and verifies idempotent reruns.
It refuses unknown/changed review evidence, unresolved similarities and modified
outputs. Augmentation now refuses writes with unresolved similarities, markup,
drafts or class issues. See the [training handoff](../docs/data_preparation/TRAINING_READINESS.md).

The augmentation command now defaults to `data/labelled/2026-10-24-clean-v1/`
as its source and `data/training/2026-10-24-eds-v1/` as its final output. All
new augmented exports must be under `data/training/`; use `--output` for a new
version. Models load the complete final version, including its separate
`train/`, `valid/` and `test/` folders.
