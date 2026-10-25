# Project datasets

Image payloads, annotations and generated exports stay local. Git tracks code,
documentation and checksum/sample manifests. Ignoring data does not back it up.

```text
data/
  IMAGE_CATEGORIES.md                     # Overlapping scene coverage categories
  manifests/                             # Tracked inventory and reviewed sample paths
  raw/<cutoff>/                          # Collected original images
    splits/{train,valid,test}/            # Existing frozen annotation inputs
  labelled/<cutoff>/{train,val,test}/     # Accepted images and _annotations.coco.json
  training/<version>/{train,valid,test}/  # Final model inputs: originals + train variants
  processed/<cutoff>/<recipe>/            # Historical exports
```

`2026-10-24` contains the current images; `2026-10-30` is an empty placeholder.
Cutoff names do not establish whether batches are cumulative. `val` and `valid`
are accepted validation aliases; do not create both for the same accepted export.

## Phase handoffs

1. Inspect/deduplicate raw originals and freeze grouped splits before annotation.
2. Annotate existing splits. Experimental drafts remain under
   `experiments/eds_autodistill/outputs/`; review/correct them before accepting.
3. Place accepted plain images and COCO JSON in `labelled/<cutoff>/`. Rendered
   boxes belong in previews, not the input image pixels.
4. Build `training/<version>/` from the cleaned labelled source. `train/` contains
   both original and augmented images; `valid/` and `test/` contain unchanged
   original images and COCO JSON. Models use this complete versioned export.
   Accepted pre-augmentation originals remain in `labelled/`.

Commands and phase context: [scripts](../scripts/README.md),
[recipe](../docs/data_preparation/README.md),
[annotation guide](../docs/annotation/guide.md).
Existing labelled splits are never silently moved or regenerated.

## Manifests and retrieval

See [manifests/README.md](manifests/README.md). `2026-10-24.csv` records the
historical 898-file snapshot before subsequent local folder changes. Its old
`roboflow/` paths are historical, not current loader paths. Do not edit it to
make a new dataset appear equivalent. A new export needs its own recipe/version
and checksums. The reviewed preview manifest references actual current paths.

Shared storage and automated download are not configured. Obtain the exact
snapshot from the maintainer. Record source, permission and capture group for
new data; use shared storage or DVC for payload versions if configured later.
Dataset removal from the current Git tree does not remove earlier historical
copies. No history rewrite is part of this workflow.

## Current training inputs

Use **`training/2026-10-24-eds-v1/`** for model training and evaluation:
411 train (137 originals + 274 augmented), 39 validation, 20 test.
`labelled/2026-10-24-clean-v1/` is its reviewed source before augmentation.
The original accepted export remains intact. `processed/` is historical;
its verified clean export was relocated into the final training directory.
See [training/README.md](training/README.md) for the exact layout and defaults.
See the [readiness handoff](../docs/data_preparation/TRAINING_READINESS.md)
for verified counts, class mapping and limitations.
