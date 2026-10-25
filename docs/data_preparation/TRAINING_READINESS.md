# Training handoff — 25 October 2026

The accepted COCO export passes the automated checks for a detector baseline.
The accepted original source is **`data/labelled/2026-10-24/`**: the former
cleaned export now uses the canonical date folder. Its superseded 199-image
predecessor has been removed. Models use **`data/training/2026-10-24/`**.

| Export | Training images | Validation images | Test images |
| --- | ---: | ---: | ---: |
| Accepted originals `data/labelled/2026-10-24` | 137 | 39 | 20 |
| Final `data/training/2026-10-24` | 411 | 39 | 20 |

The accepted originals have 548 training boxes, 154 validation boxes and 83 test boxes.
All 22 zero-box examples remain (16/4/2). Their contact sheet shows rear views,
non-target signage, or scenes without a visible eligible display; this visual
check does not establish the annotation platform's historical Null status.

## Leakage repair

The three pairs in the original export were visually inspected. Two contain
the same interchange scene in training and validation/test; the third contains
a training image with drawn-on boxes matching a clean validation image.
The accepted source's local `preparation_manifest.json` retains the reviewed
exclusions and source/output hashes.

The three training copies were excluded before promoting the accepted source
to the canonical date folder. The older uncleaned export has been removed;
validation/test image and JSON bytes remain unchanged. No held-out image moves
into training. The accepted export has no exact decoded
pixel overlap or cross-split dHash matches at distance <= 4, no `annotated_`
images, and no explicitly unreviewed drafts. COCO identities, image sizes,
category consistency and bounding-box geometry pass the existing loader checks.

The accepted export's local `preparation_manifest.json` freezes source hashes,
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
python scripts/00_audit_dataset.py --report .runtime/labelled-audit.json
python scripts/03_augment_dataset.py --write
python -m unittest discover -s tests -v
```

Model trainers use the final `data/training/2026-10-24/` export.
Its training split already combines 137 originals and 274 augmented images.
Validation/test remain separate and unaugmented. Account for the offline recipe
when configuring any additional trainer augmentation. `TRAINING_DATASET` in
`src/data_preparation/config.py` selects this version, and `load_coco_splits()`
loads it by default. `data/labelled/` remains the annotation source.

The accepted source and final export retain their original file checksums after
the directory renames. Superseded labelled and processed exports have been
removed; the current source and torchvision training version remain.
The raw `splits/` directory is an earlier annotation input; pair each COCO JSON
only with the images in its own export.

## Current code checks

Export loading now verifies frozen file checksums and complete augmentation
provenance. Optional normalization statistics use original training rows only;
validation/test cannot be used to fit them. The audit can remediate reviewed
exact overlaps, and new augmentation exports must pass a cross-split similarity
check before publication. See the [pipeline review](OUTSTANDING_ISSUES.md) for
regression coverage and the remaining evidence requirements.

## Limits of this readiness check

Similarity is a heuristic, not proof that all photos or frames are independent.
Capture/recording provenance is incomplete, so grouping all frames by their true
recording remains open. This run does not certify every positive box's semantics,
small-text readability for an unspecified model size, or every source's usage
permission. Those remain in the [pipeline review](OUTSTANDING_ISSUES.md).
Use the [annotation guide](../annotation/guide.md) for further label review.

This export supports detector development. OCR fine-tuning still needs verified
text transcriptions, which are not supplied by these bounding-box annotations.
No model training or model accuracy evaluation was run.

Image payloads and generated exports remain local under the repository's existing
ignore rules. Git contains the code, handoff and notebook sample metadata;
pushing Git does not distribute the dataset. The unused `models_old/` archive
has been removed from the working tree. Git history is unchanged.
