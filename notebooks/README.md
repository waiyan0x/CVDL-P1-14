# Notebooks

## Detector research and benchmark

[object_detection_benchmark.ipynb](object_detection_benchmark.ipynb) contains the
four-class YOLO11n, YOLO11s and DETR experiment protocol. It audits a verified
COCO export, converts it for YOLO without changing the source, trains candidates,
and reports per-class mAP, negative-image false positives and latency across the
train/validation/held-out-test splits. It also explains YOLO losses and records
the object detection tasks still outstanding. Its saved progress section records
the completed YOLO11n run and the interrupted YOLO11s run. DETR and the common
benchmark have not run. Training and benchmarking are paused by default.
The first cell has a master training switch plus separate YOLO11n, YOLO11s and
DETR switches; each model has its own training cell for inspection.

The benchmark defaults to the local manifest-backed
`data/training/2026-10-30-torchvision/` export built from the uploaded accepted
labels. It needs separate model dependencies before training.
The curated `data/samples/` gallery is for qualitative inspection and cannot
replace the labelled export. The source for the notebook is maintained in
[build_object_detection_benchmark.py](build_object_detection_benchmark.py).

On this Windows checkout, `venv/detector/` is the ignored detector environment.
It reuses the installed CUDA PyTorch build and has Ultralytics, Transformers,
TorchMetrics, pycocotools and Notebook installed. Launch from the repository root
with `venv\detector\Scripts\python.exe -m notebook`, open the benchmark notebook,
and choose the **CVDL Detector (CUDA)** kernel.

## Data preparation visual checks

Open [data_visual_checks.ipynb](data_visual_checks.ipynb) and Run All with a kernel
that has the root `requirements.txt` installed. Run from here or the repository
root; image paths are resolved against the repository automatically.

The notebook has only two displays:

1. Whole-image before/after pairs from three original training images, separately for
   brightness, rotation, salt/pepper noise and Gaussian blur. Fixed endpoint
   parameters make individual effects visible; the production export randomly
   combines transforms. Each pair shows the complete image with no bbox crops or overlays.
2. One Matplotlib row of three manually reviewed examples for each of the eight
   scene categories in [IMAGE_CATEGORIES.md](../data/IMAGE_CATEGORIES.md).

Sample filenames, hashes and observations live in
[preview_samples.json](preview_samples.json).
This JSON is used only by the visual notebook and its plotting helpers.
The preparation and model-data loading commands do not use it.
The samples are illustrative examples, not exhaustive category assignments. Rear views
and information screens illustrate exclusions, not new bbox classes. Missing or
changed sample files raise an actionable error; no substitute image is invented.

Transforms run only in memory for plotting. The visual notebook never writes datasets,
generates labels, downloads models, resplits images or performs model training.
Execute the [scripts](../scripts/README.md) for those preparation phases.
Plots are generated locally; commit the notebook with outputs cleared to keep
dataset images out of Git. The previous execution notebooks have been removed.

## Outstanding task-allocation checklist

- [x] Copy the uploaded dataset, audit accepted labels, and build a separate manifest-backed training export. Source permissions and capture groups, and the uploaded Roboflow export's missing provenance, still need review.
- [ ] Review all four class definitions and negative examples with Jy; inspect route/destination ambiguity and missing boxes. Confirm source/recording groups do not cross splits.
- [ ] Fine-tune YOLO11n, YOLO11s and DETR on identical reviewed splits; save checkpoints, settings, versions and training curves.
- [ ] Validate all four classes, negatives and speed on target hardware; inspect small, distant, blurred, angled and occluded failures and OCR crop quality.
- [ ] Select model, confidence threshold and NMS setting using validation. Freeze settings, run held-out test once and record remaining limitations.
- [ ] Deliver selected detector checkpoint/configuration and label/box contract to the app/OCR team; verify multiple displays and camera/uploaded-video latency in the integrated system.

The historical 13-image field-detector report and sample gallery are useful references, but they do not replace this four-class, held-out evaluation.
