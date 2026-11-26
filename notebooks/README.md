# Notebooks

## Detector research and benchmark

### Google Colab GPU setup for the prepared v9 export

The current notebook starts with a Colab setup cell. The corrected v9 dataset is
`data/training/2026-11-25-roboflow-v9-stem-isolated/`; the raw
`Front EDS.v9i.coco/` export is retained separately. Upload these two ZIPs to
`MyDrive/CVDL-P1-14-colab/` in Google Drive:

- `data/training/CVDL-P1-14-v9-colab-code.zip` (notebook, training scripts,
  package code, YOLO11n/YOLO11s pretrained weights)
- `data/training/2026-11-25-roboflow-v9-stem-isolated.zip` (verified dataset)

After editing the notebook or training code, rebuild the code ZIP from the
repository root with `python scripts/package_colab_v9.py` before uploading it.
The dataset ZIP is a separate export and is not rebuilt by that command.

Keep the updated `notebooks/object_detection_benchmark.ipynb` open locally in
VS Code. Install the **Colab** extension by Google (and its Jupyter dependency),
then use the notebook's **Select Kernel > Colab > New Colab Server** option to
select a GPU machine. Sign in to Google when prompted. The notebook file stays
in the Windows workspace; its Python cells execute on the remote Colab server.
Run the setup cell first. It mounts Drive, extracts the
code and dataset under `/content/CVDL-P1-14/`, installs detector dependencies,
and sets the paths used by the later notebook cells. The dataset and YOLO
conversion scratch live on the Colab VM. Checkpoints, per-model training
results and benchmark reports are written to
`MyDrive/CVDL-P1-14-colab/results/` so they survive a runtime reset. The
existing Windows save paths remain the defaults outside Colab.

The repository notebook defaults to `RUN_TRAINING=False` and
`RUN_BENCHMARK=False`. Record the remaining v9 source-scene and annotation
review limitations when interpreting results. For a training run, choose
`TRAIN_MODEL` in the first settings cell,
set `RUN_TRAINING=True`, keep benchmark and final test off, then Run All. The
same `RUN_ID` is used for the three separate model runs. Do not rerun a model
under an existing ID because the trainer refuses to overwrite its checkpoint.

The setup cell is also maintained in
[colab_v9_setup_cell.py](colab_v9_setup_cell.py); the notebook contains an
embedded copy so it can run before the repository is extracted.

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

Measured benchmarks display **separate Train, Validation, and Test tables**.
The Test section stays marked as held out until `RUN_FINAL_TEST=True`. Each
class row shows box count, mAP50, mAP50:95 and mAR@100 recall. The tables are
also saved beside the benchmark JSON as `benchmark_*_tables.md`; saved v4
figures remain historical and are not copied into the v9 tables.

### V9 YOLO baseline and tuning status

The v9 training CSVs viewed during the Colab session recorded best validation
mAP50:95 of `0.67547` for
YOLO11n (epoch 8) and `0.69106` for YOLO11s (epoch 9). These are Ultralytics
validation metrics, not a common two-model benchmark or held-out test. The v9
CSVs and weights have not been copied into this repository. No v9 DETR mAP or
tuned-variant result is recorded. YOLO11s was interrupted and later resumed;
its final epoch and files still need verification from Drive. See
[the v9 status page](../docs/OBJECT_DETECTION_V9_STATUS.md). A [reviewed v4 validation overlay](../Obj-Dect-OCR/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/overlays/success_02.jpg)
illustrates the four EDS bounding-box classes; it is an example image, not v9
evaluation evidence.

The notebook includes two disabled YOLO11s experiments after baseline training:
`gentle_aug` adds small translation, scale and brightness changes;
`localization` raises image size from 640 to 800 and box-loss gain from 7.5 to
8.5, with batch size 16 for GPU memory. Both use fresh pretrained weights,
save to new folders, and require `RUN_TUNING=True`. Compare their measured
validation scores before running a final test. The v9 source and annotation
review remains open.

The benchmark now defaults to the prepared, manifest-backed
`data/training/2026-11-25-roboflow-v9-stem-isolated/` export. Set the run flags
for each model or evaluation pass. The repository copy is paused by default.
For validation of the two completed YOLO runs, set `RUN_BENCHMARK=True`,
`RUN_FINAL_TEST=False`, and `BENCHMARK_MODELS=('yolo11n', 'yolo11s')`.
After selecting one model and threshold on validation, use a one-item model
tuple and set `RUN_FINAL_TEST=True` while keeping `RUN_BENCHMARK=True`.
The earlier
`data/training/2026-11-05-roboflow-v4-reviewed/` export's completed
`v4-reviewed-01` run has a [saved three-model validation comparison and selected
YOLO11s final test](../Obj-Dect-OCR/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md).
The older `2026-10-30-torchvision` dataset and `baseline-01` results are
preserved. Separate model dependencies are needed before training.
The curated `data/samples/` gallery is for qualitative inspection and cannot
replace the labelled export. The source for the notebook is maintained in
[build_object_detection_benchmark.py](build_object_detection_benchmark.py).

On this Windows checkout, `venv/detector/` is the ignored detector environment.
It reuses the installed CUDA PyTorch build and has Ultralytics, Transformers,
TorchMetrics, pycocotools and Notebook installed. Launch from the repository root
with `venv\detector\Scripts\python.exe -m notebook`, open the benchmark notebook,
and choose the **CVDL Detector (CUDA)** kernel.

The notebook retains saved v4 outputs, but its older written `baseline-01`
table is historical. Read the v4 `RESULTS.md` and archived JSON reports for
those measurements. Both v4 final-test reports are complete; avoid running
either test again for threshold selection. Use a new run ID for v9 experiments.
The later [v4 validation NMS/crop review](../Obj-Dect-OCR/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/REVIEW.md)
compares `0.50` and `0.70` without reopening the test. The tested v4
configuration remains NMS `0.70`.

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
[saved results](../Obj-Dect-OCR/object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md)
and [review packet](../Obj-Dect-OCR/object_detection/bf938f526d2c/runs/baseline-01/data_review/REVIEW.md).

The historical 13-image field-detector report and sample gallery are useful
references, but they do not replace this four-class, held-out evaluation.
