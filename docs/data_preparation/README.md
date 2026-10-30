# Preparation phases

The scripts run independently. Each reads files saved by the previous phase;
no notebook kernel or variables are required. Commands run from the repository root.

## 1. Inspect, group and split

`scripts/01_prepare_and_split.py` decodes raw images with OpenCV, excludes
`annotated_` copies, deduplicates decoded pixels, and groups similar scenes.
Pillow supplies the AVIF codec when a source file's extension is misleading.
An optional `source,group` CSV joins frames from the same recording or capture.
Similarity is a review heuristic, not proof that unrelated files are independent.

Scikit-learn `GroupShuffleSplit` targets 70/20/10 train/validation/test by groups,
so image proportions are approximate. `--write` copies into a new raw split
directory and freezes source hashes, settings and membership in `manifest.json`.
Raw originals are preserved. Never rerun a different split over annotated data.
The current `splits/` already contains images; use it as the annotation input.

## 2. Annotate and review

`scripts/02_auto_annotate.py` uses a local Autodistill Grounding DINO adapter.
It plans by default; `--run` explicitly downloads weights and generates proposals.
See the [annotation README](../annotation/README.md) and
[annotation guide](../annotation/guide.md) for scope and classes.

Draft output stays under `experiments/eds_autodistill/outputs/<run>/`, with plain
images and COCO JSON separate from rendered overlays. It never writes accepted
labels automatically. Use the
[local box editor](../annotation/README.md#local-box-editor-no-additional-dependencies)
to correct boxes, confirm positives/negatives and export accepted labels to
`data/labelled/<cutoff>/{train,val,test}`. The editor opens after inference with
`--review`; automatic checks flag structural issues but do not confirm semantic
correctness. External editors may instead mark image `review_status` as
`accepted` and copy the reviewed export manually. Existing manual exports are accepted
without requiring this experimental metadata. Keep the original split membership.

## 3. Validate and augment

`scripts/03_augment_dataset.py` checks COCO IDs, classes, image dimensions, boxes,
negative examples and duplicate pixels. It reports similar scenes across splits
for review and refuses explicitly unreviewed draft images. COCO boxes use
`[x, y, width, height]`; nested panel and content boxes remain distinct objects.

| Enabled transform | Range | Reason |
| --- | --- | --- |
| Brightness | 0.90–1.10 factor | Mild lighting changes without washing out LEDs |
| Rotation | −3° to +3° | Camera tilt with paired image and bounding-box transforms |
| Salt/pepper noise | 1% expected pixel rate | Mild sensor corruption; channels change together |
| Gaussian blur | sigma sampled 0–1 pixel; kernel up to 7 | Slight defocus; inspect thin text for loss of readability |

Torchvision v2 applies geometry to images and boxes together. Rotation uses a
padded canvas to retain the original scene. Seeds derive from the source hash,
variant number and configured seed. Only training expands: the default multiplier
of 3 means one original plus two variants, all together in the final
`data/training/<cutoff>/train/`.
Validation/test images and JSON are copied byte-for-byte. Null images keep no boxes.

Flips, 90° rotation, crops, shear, cutout and mosaic are disabled to protect
readable text and complete panels. Exposure, hue, saturation, grayscale, motion
blur and gain are disabled to avoid redundant or unrealistic corruption.

`--write` stages a complete export before publishing it. The manifest records
source hashes, parameters, library versions, this recipe's hash, provenance and
output checksums. Changed inputs/settings or modified exports require a new
dataset version. The default source is `data/labelled/2026-10-24/`;
the final output is `data/training/2026-10-24/`. Superseded augmentation
exports under `data/processed/` have been removed. The recipe hash uses a
[frozen reference](recipes/README.md)
so current workflow documentation can evolve without changing dataset identity.

### Reviewed visual comparisons

Three original training examples cover a sheltered stop (176), daylight (131M)
and night (120). The notebook compares whole images without bbox crops or overlays.
On visual review, 10% dimming retains the visible
layout; 3° rotation tilts the scene while the panel remains visible; 1% noise
adds speckles over thin strokes; sigma-1 blur noticeably softens the smallest
letters in the 176 panel. These visual observations do not measure model
accuracy. Check readability at the actual model input size before accepting a
recipe; reduce/disable blur if the required text becomes unreadable.

## 4. Loading and model-specific preprocessing

Models use `data/training/2026-10-24/` as their complete dataset root.
`TRAINING_DATASET` in `config.py` selects the current version.
The current local inventory is **420 train, 39 validation and 20 test images
(479 total)**, verified on 2026-10-29. Training metadata has 140 source names
with three outputs each; exact original/variant provenance is unavailable.
The COCO identifies a Roboflow export, not a verified build of this recipe.
`load_coco_splits()` requires a manifest at this configured path, but the current
folder has none and will be rejected. See [the current training inventory](../../data/training/README.md).
Keep these splits separate during model fitting and evaluation. `labelled/`
remains the reviewed source used to build the final dataset.


`src/data_preparation/datasets.py` supplies the existing PyTorch Dataset and
variable-size detection collate function. `preprocessing.py` provides optional
letterbox resizing, tensor conversion/scaling to [0, 1], train-only statistics
and normalization. No model training or fixed model size is included.

Retain native uint8 RGB images on disk. Choose resizing and normalization when a
specific pretrained detector is selected; avoid applying its preprocessing twice.
Fit any dataset statistics on original training images only. The visual notebook
never computes a training dataset, labels, splits or normalization statistics.
