# Project datasets

Image payloads, annotations and generated exports stay local. Git tracks code,
documentation and checksum/sample manifests. Ignoring data does not back it up.

```text
data/
  IMAGE_CATEGORIES.md                     # Overlapping scene coverage categories
  DATA_PREP_TODO.md                       # Remaining dataset/project work
  manifests/                             # Tracked inventory and reviewed sample paths
  raw/<cutoff>/                          # Collected original images
    splits/{train,valid,test}/            # Existing frozen annotation inputs
  labelled/<cutoff>/{train,val,test}/     # Accepted images and _annotations.coco.json
  processed/<cutoff>/<recipe>/{train,valid,test}/
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
4. Augment training only. `processed/train` contains both original and augmented
   images; accepted pre-augmentation originals remain in `labelled/train`.
   Validation/test images and JSON are copied unchanged.

Commands and phase context: [scripts](../scripts/README.md),
[recipe](../docs/data_preparation/README.md),
[annotation guide](../eds_layout_and_annotation_guide.md).
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
