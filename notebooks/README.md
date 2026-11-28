# Notebooks

## Local v9 object detection benchmark

Open [object_detection_benchmark.ipynb](object_detection_benchmark.ipynb) in VS Code with the `CVDL Detector (CUDA)` kernel. It uses the verified [v9 COCO export](../data/training/README.md). Seven model runs, validation comparisons, and one selected-model final test are saved; start with the [v9 results index](../Object-Detection-v9/RESULTS.md). The historical v4 tables in the notebook use different data.

The recorded baseline run ID is `v9-local-01`; A/B variants use `v9-tuning-01`. All execution switches should remain `False` when reviewing saved results. The held-out v9 test is closed for further model selection. Check the first code cell before Run All: a working notebook can retain active switches and old outputs.

For a **new** training comparison, choose a new run ID, audit the dataset, and enable one training switch at a time. `RUN_TRAINING` handles YOLO11n/s or DETR baselines; `RUN_TUNING` handles one YOLO A/B variant. Starting weights are published pretrained models, not prior EDS checkpoints. The trainer refuses existing model folders and does not resume. Baseline YOLO used batch 32 and four workers; DETR used two-image microbatches accumulated to an effective 32. Exact settings for each completed run are linked from the results index.

The benchmark cell reports train and validation for the names in `BENCHMARK_MODELS`; it evaluates test only when `RUN_FINAL_TEST=True`. The saved v9 final test used `('yolo11s-gentle_aug',)` alone, with confidence `0.50` and NMS IoU `0.70`. Its [JSON report](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test.json) and [split tables](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test_tables.md) are preserved.

The [A/B experiment document](../docs/OBJECT_DETECTION_YOLO_TUNING_PLAN.md) explains the four completed variants and the batch-16 change used by both 800-pixel B runs. The notebook's section 3B is retained for a new, separately named experiment.

The evaluator loads each completed candidate's best checkpoint and saved image size. `BENCHMARK_MODEL_RUNS` can map candidates stored under another run ID. The selected model is still a research result; the deployed application detector remains the reviewed-v4 checkpoint.

Run folders, benchmark JSON, split tables, and checkpoints are in [Object-Detection-v9](../Object-Detection-v9/README.md); identical YOLO weight backups are under [YOLO_Weights/v9](../YOLO_Weights/v9/README.md). These files are tracked through Git/Git LFS. The [v4 archive](../Object-Detection-v4/README.md) remains separate. The notebook does not mount Google Drive.

The notebook source is maintained in [build_object_detection_benchmark.py](build_object_detection_benchmark.py). Regenerating the notebook clears saved cell outputs; it never executes training. Preserve the executed notebook when editing narrative or comments.

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

## Historical v4 task-allocation checklist

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
