# Project datasets

Image payloads, annotations and generated exports stay local. Git tracks code,
documentation and the notebook's preview sample metadata. Ignoring data does not
back it up.

```text
data/
  IMAGE_CATEGORIES.md                     # Overlapping scene coverage categories
  raw/<cutoff>/                          # Collected original images
    splits/{train,valid,test}/            # Existing frozen annotation inputs
  labelled/<cutoff>/{train,val,test}/     # Accepted images and _annotations.coco.json
  training/<version>/{train,valid,test}/  # Final model inputs: originals + train variants
```

`2026-10-24` contains the current source images; unused empty batch placeholders
have been removed.
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

## Export integrity and retrieval

The labelled and training exports keep their own local integrity manifests
beside their payloads. These record source/output hashes and augmentation
provenance and are checked by the loader. Keep them with their dataset versions.
COCO JSONs contain the training annotations. The removed `data/manifests/`
inventory/report folder is not needed by the current pipeline.

The visual notebook's sample paths, hashes and observations live separately in
[notebooks/preview_samples.json](../notebooks/preview_samples.json). No preparation
or model-loading command depends on that notebook metadata.

Shared storage and automated download are not configured. Obtain the exact
snapshot from the maintainer. Record source, permission and capture group for
new data; use shared storage or DVC for payload versions if configured later.
Dataset removal from the current Git tree does not remove earlier historical
copies. No history rewrite is part of this workflow.

## Current training inputs

Use **`training/2026-10-24-eds-v1/`** for model training and evaluation:
411 train (137 originals + 274 augmented), 39 validation, 20 test.
`labelled/2026-10-24/` is the accepted original source before augmentation:
137 train, 39 validation and 20 test images. It contains the former cleaned
export, promoted to the canonical date folder. The superseded 199-image export
and the separate cleaned-name folder have been removed. Only the current
torchvision training version is retained;
`data/processed/` and its superseded exports have been removed.
See [training/README.md](training/README.md) for the exact layout and defaults.
See the [readiness handoff](../docs/data_preparation/TRAINING_READINESS.md)
for verified counts, class mapping and limitations.
