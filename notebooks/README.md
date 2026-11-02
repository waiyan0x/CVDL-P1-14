# Notebooks

## Detector research and benchmark

[object_detection_benchmark.ipynb](object_detection_benchmark.ipynb) contains the
four-class YOLO11n, YOLO11s and DETR experiment protocol. It audits a verified
COCO export, converts it for YOLO without changing the source, and reports
per-class mAP, negative-image false positives and latency across the
train/validation/held-out-test splits. It also explains YOLO losses and records
the object detection tasks still outstanding. The earlier Section 3 and all
earlier saved model runs were removed. The current notebook has a small manual
training launcher backed by `scripts/train_object_detection.py`: select one
model, use one `RUN_ID` for the three-model comparison, enable training, and
click Run All. The same notebook then performs validation and test reporting in
separate runs.

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

The `baseline-01` commands below have already completed and are retained only as
the reproducibility record. Do **not** rerun them with the same run ID: training
refuses to overwrite an existing model folder. Use a new run ID only after a new
reviewed dataset version or a deliberately changed experiment is ready.

```powershell
venv\detector\Scripts\python.exe scripts\train_object_detection.py --model yolo11n --run-id baseline-01
venv\detector\Scripts\python.exe scripts\train_object_detection.py --model yolo11s --run-id baseline-01
venv\detector\Scripts\python.exe scripts\train_object_detection.py --model detr-resnet-50 --run-id baseline-01
```

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
[saved results](../evaluation/object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md)
and [review packet](../evaluation/object_detection/bf938f526d2c/runs/baseline-01/data_review/REVIEW.md).

The historical 13-image field-detector report and sample gallery are useful
references, but they do not replace this four-class, held-out evaluation.
