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
  training/<cutoff>/{train,valid,test}/  # Final model inputs: originals + train variants
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
4. Build `training/<cutoff>/` from the cleaned labelled source. `train/` contains
   both original and augmented images; `valid/` and `test/` contain unchanged
   original images and COCO JSON. Models use this complete versioned export.
   Accepted pre-augmentation originals remain in `labelled/`.

Commands and phase context: [scripts](../scripts/README.md),
[recipe](../docs/data_preparation/README.md),
[annotation guide](../docs/annotation/guide.md).
Existing labelled splits are never silently moved or regenerated.

## Export integrity and retrieval

The pipeline expects local integrity manifests beside export payloads. These
record source/output hashes and augmentation provenance and are checked by the
loader. The current local training folder is missing its expected manifest;
see the inventory and loading limits below. Keep existing manifests with their versions.
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

The current **`training/2026-10-24/`** local inventory is **479 images**:
420 train, 39 validation, 20 test (verified against image files and COCO records
on 2026-10-29). Its Roboflow training metadata records 140 source names with three
outputs each; it does not establish which outputs are originals. The older
411-image training / 470-image total description no longer matches this folder.

`labelled/2026-10-24/` remains a separate accepted source of **196 images**:
137 train, 39 validation (`val/`) and 20 test. The raw folder has **212 top-level
images** plus **198 frozen split copies** (138/40/20); do not count split copies
as additional collected photos. [samples/](samples/README.md) contains eight
coverage examples and four isolated augmentation demonstrations, excluded from
all dataset counts above.

The current training folder lacks the export manifest required by the configured
loader; do not assume it is a verified torchvision build or that validation/test
images are unchanged copies of the labelled export. See
[training/README.md](training/README.md) for current inventory, provenance limits
and safe rebuild instructions. Earlier readiness reports describe a prior export.
