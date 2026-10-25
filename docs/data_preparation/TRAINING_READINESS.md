# Training handoff — 25 October 2026

The cleaned COCO export passes the automated checks for a detector baseline.
The [machine-readable verification](../../data/manifests/2026-10-25-readiness.json)
records the initial counts, checksums, preserved holdouts and test results.
The [layout verification](../../data/manifests/2026-10-25-training-layout.json)
records the final model-input location and unchanged export checksums.
The original labelled export and the older processed exports contain known
cross-split scene overlaps. Models use **`data/training/2026-10-24-eds-v1/`**.
The labelled directories below are annotation sources.

| Export | Training images | Validation images | Test images |
| --- | ---: | ---: | ---: |
| Original `data/labelled/2026-10-24` | 140 | 39 | 20 |
| Clean `data/labelled/2026-10-24-clean-v1` | 137 | 39 | 20 |
| Final `data/training/2026-10-24-eds-v1` | 411 | 39 | 20 |

The clean export has 548 training boxes, 154 validation boxes and 83 test boxes.
All 22 zero-box examples remain (16/4/2). Their contact sheet shows rear views,
non-target signage, or scenes without a visible eligible display; this visual
check does not establish the annotation platform's historical Null status.

## Leakage repair

The three pairs in the original export were visually inspected. Two contain
the same interchange scene in training and validation/test; the third contains
a training image with drawn-on boxes matching a clean validation image. The
[reviewed exclusions](../../data/manifests/2026-10-24-training-exclusions.json)
record every filename, reason and both image checksums.

Cleaning excludes these three training copies in a new export. It preserves
the original accepted export and all validation/test image and JSON bytes.
No held-out image moves into training. The clean export has no exact decoded
pixel overlap or cross-split dHash matches at distance <= 4, no `annotated_`
images, and no explicitly unreviewed drafts. COCO identities, image sizes,
category consistency and bounding-box geometry pass the existing loader checks.

The cleaned export's local `preparation_manifest.json` freezes source hashes,
decisions, the audit and every output checksum. The augmented export has its
own `augmentation_manifest.json` recording source hashes, recipe and provenance.
Reruns reject changed sources, review evidence or output files.

## Class mapping for training

The export contains an unused parent category `0: front-eds`, with zero boxes.
It is not an additional foreground class. Preserve the COCO JSON and map by
category ID when integrating a model:

| COCO ID | Name | Requested zero-based training index |
| ---: | --- | ---: |
| 1 | `front_eds` | 0 |
| 3 | `front_eds_num` | 1 |
| 4 | `front_eds_route` | 2 |
| 2 | `front_eds_destination` | 3 |

The existing `DetectionDataset` returns original COCO IDs; it does not apply this
mapping automatically. Frameworks reserving label zero for background need their
own mapping, such as foreground IDs 1–4. Do not pass `len(categories) == 5` as
the number of foreground classes or infer labels from category-list order.

## Reproduce and use

Run from the repository root with the project's Python environment:

```powershell
python scripts/00_audit_dataset.py --write --report .runtime/clean-label-audit.json
python scripts/00_audit_dataset.py --input data/labelled/2026-10-24-clean-v1
python scripts/03_augment_dataset.py --write
python -m unittest discover -s tests -v
```

Model trainers use the final `data/training/2026-10-24-eds-v1/` export.
Its training split already combines 137 originals and 274 augmented images.
Validation/test remain separate and unaugmented. Account for the offline recipe
when configuring any additional trainer augmentation. `TRAINING_DATASET` in
`src/data_preparation/config.py` selects this version, and `load_coco_splits()`
loads it by default. `data/labelled/` remains the annotation source.

The verified export was relocated from
`data/processed/2026-10-24/eds-torch-v2-clean-v1/` without modifying any image,
COCO JSON or augmentation-manifest bytes. That old path in the initial
readiness report is historical; `data/processed/` now holds older exports.
The raw `splits/` directory is an earlier annotation input; pair each COCO JSON
only with the images in its own export.

## Limits of this readiness check

Similarity is a heuristic, not proof that all photos or frames are independent.
Capture/recording provenance is incomplete, so grouping all frames by their true
recording remains open. This run does not certify every positive box's semantics,
small-text readability for an unspecified model size, or every source's usage
permission. Those remain in the [data checklist](../../data/DATA_PREP_TODO.md).
Use the [annotation guide](../annotation/guide.md) for further label review.

This export supports detector development. OCR fine-tuning still needs verified
text transcriptions, which are not supplied by these bounding-box annotations.
No model training or model accuracy evaluation was run.

Image payloads and generated exports remain local under the repository's existing
ignore rules. Git contains the code, reviewed exclusion checksums and handoff;
pushing Git does not distribute the dataset. Old checkpoints are archived in
`models_old/`, with the TrOCR checkpoint managed by Git LFS.
