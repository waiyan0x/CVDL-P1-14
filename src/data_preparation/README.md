# Reusable preparation code

Use the [standalone scripts](../../scripts/README.md) to execute phases and the
[visual notebook](../../notebooks/README.md) to inspect samples. Modules perform
no inference or pipeline writes when imported. Imports resolve from `src/`;
scripts and the notebook add that path explicitly.

| Module | Responsibility |
| --- | --- |
| `config.py` | Repository paths, final `TRAINING_DATASET` and split/augmentation settings |
| `images.py` | OpenCV decoding/encoding, codec fallback, hashes and similarity fingerprints |
| `splitting.py` | Raw inventory, duplicate grouping, split plan and frozen copies |
| `annotation.py` | Autodistill model adapter, draft proposals and isolated export |
| `annotation_cli.py` | Dependency-light plan/help commands; model imports deferred until `--run` |
| `readiness.py` | Readiness audit and checksum-bound, versioned training exclusions |
| `datasets.py` | Verified COCO loading, provenance tags, leakage candidates and PyTorch Dataset helpers |
| `manifests.py` | Frozen export file checksums and complete training provenance |
| `augmentation.py` | Seeded paired image/box transforms and atomic training export |
| `preprocessing.py` | Optional letterbox, scaling and normalization for later model integration |
| `visualization.py` | Read-only Matplotlib comparisons and category sample plots |

Phase inputs, outputs and justifications are in
[docs/data_preparation/README.md](../../docs/data_preparation/README.md).
Image coverage categories describe scenes; COCO classes describe objects inside
those scenes. They are separate concepts and need separate records.

`load_coco_splits()` defaults to `config.TRAINING_DATASET`, currently
`data/training/2026-10-24-eds-v1/`. Preparation commands pass their explicit
source paths; future model trainers should load this final dataset root.
The final `train/` combines originals and augmented images; its `valid/` and
`test/` contain unchanged originals. The augmentation exporter writes only
under `data/training/` and hashes the frozen recipe reference from `config.py`.

Frozen export checksums are verified when loading. Loaded split dictionaries
include `split`, and each training row has `augmentation_variant` (0 for an
original). `fit_training_statistics()` requires the training split and skips
augmented variants. An audit may pass `allow_cross_split_duplicates=True` to
inspect/remediate exact overlaps; ordinary loading rejects them.
