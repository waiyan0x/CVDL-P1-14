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
labels automatically. Correct missed/incorrect boxes, confirm negatives, and
mark draft image `review_status` as `accepted` before copying the reviewed export
to `data/labelled/<cutoff>/{train,val,test}`. Existing manual exports are accepted
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
of 3 means one original plus two variants, all together in processed/train.
Validation/test images and JSON are copied byte-for-byte. Null images keep no boxes.

Flips, 90° rotation, crops, shear, cutout and mosaic are disabled to protect
readable text and complete panels. Exposure, hue, saturation, grayscale, motion
blur and gain are disabled to avoid redundant or unrealistic corruption.

`--write` stages a complete export before publishing it. The manifest records
source hashes, parameters, library versions, this recipe's hash, provenance and
output checksums. Changed inputs/settings or modified exports require a new
output directory. The current recipe documentation differs from older runs;
the CLI therefore defaults to a new `eds-torch-v2` output. Existing v1 data stays local.

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

`src/data_preparation/datasets.py` supplies the existing PyTorch Dataset and
variable-size detection collate function. `preprocessing.py` provides optional
letterbox resizing, tensor conversion/scaling to [0, 1], train-only statistics
and normalization. No model training or fixed model size is included.

Retain native uint8 RGB images on disk. Choose resizing and normalization when a
specific pretrained detector is selected; avoid applying its preprocessing twice.
Fit any dataset statistics on original training images only. The visual notebook
never computes a training dataset, labels, splits or normalization statistics.
