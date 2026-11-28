# V9 object detection results

The [benchmark notebook](../notebooks/object_detection_benchmark.ipynb) used the
verified [v9 COCO export](../data/training/README.md), manifest SHA-256
`43159c679cbe4ea7d3b791ef106d66ce7795a10307155fbc33863205868198d7`.
The train, validation, and held-out test splits contain 6,858, 294, and 299
images. They include 579, 20, and 20 zero-box images, respectively. The same
four class IDs and source-stem-isolated splits were used throughout.

## Completed runs and validation comparison

All three baselines finished under `v9-local-01`; the four YOLO A/B variants
finished under `v9-tuning-01`. The cap was 60 epochs with seed 42. YOLO used
patience 15, optimizer `auto`, and four workers. Baselines and A used batch 32
at 640 pixels; both B runs used batch 16 at 800 pixels. B therefore changed
batch as well as resolution and box gain. DETR used a two-image GPU microbatch
with gradient accumulation to an effective batch of 32. See each run's saved
`args.yaml` or `train/settings.json` for its exact settings.

| Candidate | Epochs recorded | Input | Validation mAP50 | Validation mAP50:95 | mAR@100 | Negative FP at 0.50 | Median ms/image |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| YOLO11n | 21 | 640 | 91.4% | 63.5% | 72.0% | 9 | 14.9 |
| YOLO11s | 23 | 640 | 92.2% | 63.9% | 71.0% | 11 | 15.0 |
| DETR-ResNet50 | 60 | 640 | 88.7% | 54.3% | 66.1% | 51 | 41.2 |
| YOLO11n-A, gentle augmentation | 54 | 640 | 91.7% | 66.8% | 73.0% | 7 | 15.2 |
| YOLO11n-B, localization | 22 | 800 | 91.9% | 67.4% | 74.6% | 3 | 15.8 |
| **YOLO11s-A, gentle augmentation** | **47** | **640** | **92.0%** | **68.4%** | **74.1%** | **13** | **16.4** |
| YOLO11s-B, localization | 20 | 800 | 93.1% | 65.3% | 73.5% | 6 | 16.3 |

Negative FP is the number of detections across 20 negative **validation**
images at confidence 0.50. It is not the number of images with a false positive.
The [baseline report](object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11n_yolo11s_detr-resnet-50_validation.json)
and [YOLO A/B comparison](object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11n_yolo11s_yolo11n-gentle_aug_yolo11n-localization_yolo11s-gentle_aug_yolo11s-localization_validation.json)
contain per-class train/validation metrics, negative-image counts, latency, and
the model paths. Their adjacent `_tables.md` files give separate split tables.

Validation mAP50:95 selected YOLO11s-A. Its threshold sweep had its highest
recorded F1 at confidence 0.50; NMS IoU remained 0.70. YOLO11n-B had fewer
negative-image detections (3 versus 13) and slightly higher mAR@100, so the
choice favors overall localization AP rather than the lowest false-positive
count. The test split was not used to choose or tune the model.

## One held-out test: YOLO11s-A

The [final report](object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test.json)
and [split tables](object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test_tables.md)
record 299 test images, 1,165 boxes, and 20 negative images. At confidence
0.50 and NMS IoU 0.70, mAP50 was **90.5%**, mAP50:95 **68.2%**, and mAR@100
**74.3%**. Median/p95 detector inference time was **16.3/24.4 ms per image**
on the tested CUDA laptop. The model produced **17 detections across 20
negative images**.

| Test class | mAP50 | mAP50:95 | mAR@100 |
| --- | ---: | ---: | ---: |
| Whole EDS panel | 87.5% | 52.0% | 61.3% |
| Service number | 90.8% | 74.9% | 78.6% |
| Route / landmarks | 90.9% | 68.9% | 75.7% |
| Destination | 92.9% | 76.9% | 81.4% |

Test mAP50:95 is 0.2 percentage points below validation (68.2% versus 68.4%).
This is a report of the measured split, not a claim about unseen bus scenes.
The [selected checkpoint](object_detection/43159c679cbe/runs/v9-tuning-01/yolo11s-gentle_aug/weights/best.pt)
has SHA-256 `44bec14038815655341ddb8b9d8859ed9fe52d8223d29bcadc3cd30c1d6f3522`.
Its [status](object_detection/43159c679cbe/runs/v9-tuning-01/yolo11s-gentle_aug/status.json)
marks training, validation, and test saved. An identical backup is in
[YOLO_Weights/v9](../YOLO_Weights/v9/43159c679cbe/runs/v9-tuning-01/yolo11s-gentle_aug/best.pt).

## Artifact and review status

The seven completed run folders hold training histories, settings, and
checkpoints. All six YOLO `best.pt`/`last.pt` files match their run-local copies
and `YOLO_Weights/v9` backups by SHA-256; DETR's complete run has its saved
processor, model, settings, and 60-epoch loss history. All checkpoints are
tracked through Git LFS. The v9 dataset ZIP was removed in the detector
branch's latest cleanup; the extracted dataset remains local and is needed to
reproduce training or evaluation. The three benchmark JSON reports
and their split tables are tracked in Git. The historical v4 detector remains
the application default; this v9 result has not been installed in the app.

Human source-scene and annotation review remains open. A separate qualitative
review should describe bus type, lighting, angle, distance, missed small signs,
negative-image detections, and OCR crop quality. The final test is closed for
further model selection. The [A/B plan](../docs/OBJECT_DETECTION_YOLO_TUNING_PLAN.md)
records the experiment rationale and exact parameter differences.
