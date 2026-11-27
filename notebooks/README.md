# Notebooks

## Local v9 object detection benchmark

Open [object_detection_benchmark.ipynb](object_detection_benchmark.ipynb) from this checkout in VS Code and select the local `CVDL Detector (CUDA)` kernel. The notebook uses the verified [v9 training export](../data/training/README.md) at `data/training/2026-11-25-roboflow-v9-stem-isolated/`. The source folder is unchanged. The notebook starts with all execution switches set to `False` and no saved cell outputs.

The fresh run ID is `v9-local-01`. Training starts from the published YOLO11n, YOLO11s, and DETR pretrained weights, never from the prior EDS checkpoints. The two YOLO starting weights belong in `.runtime/object_detection_benchmark/pretrained/`. The dataset audit must report `data_ready: true` before enabling training. The raw v9 split has 6,858 train, 294 validation and 299 test images after source-stem isolation; human scene and annotation review remains open.

Train **one model at a time**. In the first code cell, set `TRAIN_MODEL` to `yolo11n`, `yolo11s`, or `detr-resnet-50`; set `RUN_TRAINING=True`; leave `RUN_BENCHMARK=False` and `RUN_FINAL_TEST=False`; then Run All. Keep the same run ID across the three models. The v9 baseline uses batch size 32 and four data-loading workers. YOLO uses a physical batch of 32. DETR uses a two-image GPU microbatch with 16 gradient-accumulation steps for an effective batch of 32, and four workers for its training loader. Epochs 60, image size 640, seed 42, and the other v4 settings stay as recorded. A new run refuses an existing model folder. The notebook does not resume a previous checkpoint.

After training, set `RUN_TRAINING=False`, `RUN_BENCHMARK=True`, and `RUN_FINAL_TEST=False` to measure train and validation on the completed models in `BENCHMARK_MODELS`. The report writes separate Train, Validation, and Test tables; Test stays pending. Choose the model and operating threshold from validation. For one held-out test, keep `RUN_BENCHMARK=True`, set `RUN_FINAL_TEST=True`, and put the selected model alone in `BENCHMARK_MODELS`.

All new raw run files, benchmark JSON, split tables, copied checkpoints and status files are saved **locally** in [Object-Detection-v9](../Object-Detection-v9/README.md), under `object_detection/<dataset-fingerprint>/runs/v9-local-01/`. YOLO `best.pt` and `last.pt` are also backed up under [`YOLO_Weights/v9/`](../YOLO_Weights/v9/README.md) at `<dataset-fingerprint>/runs/v9-local-01/<model>/`; the older root-level weights are left alone. The older [Object-Detection-v4](../Object-Detection-v4/object_detection/README.md) archive and its results are separate. Nothing in this notebook mounts Google Drive or starts training while the switches remain off.

The notebook source is maintained in [build_object_detection_benchmark.py](build_object_detection_benchmark.py). Regenerating it clears cell outputs and never executes training. Earlier v4 benchmark tables in the narrative are historical evidence, not v9 results.
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
- [x] Fine-tune YOLO11n, YOLO11s and DETR on identical current splits; save checkpoints, settings, versions and training curves.
- [x] Validate all four classes, negatives and speed on the Windows CUDA machine; inspect small, distant, blurred, angled and occluded failures and OCR crop quality.
- [x] Select YOLO11s and confidence `0.20` using validation, retain NMS IoU `0.70`, run the held-out test once and record the execution deviation and limitations.
- [ ] Compare at least two NMS IoU settings on validation if strict completion of the overlapping-box-suppression allocation is required. Do not tune this on the held-out test.
- [x] Deliver the selected detector checkpoint contract/configuration and label/box contract; verify multiple displays, uploaded-video decode and a simulated camera path. Physical-camera and moving-bus field testing remain pending integration evidence.

The human data review remains a prerequisite for declaring the dataset final. If
it changes labels or split groups, publish a new dataset version and rerun all
three models under a new run ID; otherwise preserve `baseline-01` without rerunning
the held-out test. See the [Cody handoff](../docs/OBJECT_DETECTION_HANDOFF.md),
[saved results](../Object-Detection-v4/object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md)
and [review packet](../Object-Detection-v4/object_detection/bf938f526d2c/runs/baseline-01/data_review/REVIEW.md).

The historical 13-image field-detector report and sample gallery are useful
references, but they do not replace this four-class, held-out evaluation.
