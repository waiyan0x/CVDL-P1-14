# Object detection baseline-01 results

Recorded on 2 November 2026 from the saved benchmark JSON files. Dataset manifest SHA-256: `bf938f526d2c01f1960b9af018f1fd1dc78a431e725037c84d1707dfcc5b826c`.

## Experimental settings

- Models: YOLO11n, YOLO11s, DETR-ResNet50
- Classes: `front_eds`, `front_eds_num`, `front_eds_route`, `front_eds_destination`
- Dataset: 411 train, 39 validation, 20 test images
- Input size: 640
- Seed: 42
- Device: CUDA on Windows 11
- PyTorch: 2.11.0+cu128
- Ultralytics: 8.3.158
- Transformers: 4.57.6
- TorchMetrics: 1.9.0

## Overall benchmark

| Candidate | Train mAP50 / mAP50:95 | Validation mAP50 / mAP50:95 | Test mAP50 / mAP50:95 | Test median / p95 ms | Test negative FP |
|---|---|---|---|---|---:|
| YOLO11n | 0.8910 / 0.7451 | 0.5709 / 0.3466 | 0.7165 / 0.4139 | 40.21 / 123.25 | 0 |
| **YOLO11s** | **0.9140 / 0.8024** | **0.6734 / 0.4274** | 0.7077 / 0.3938 | **34.22** / 128.14 | 0 |
| DETR-ResNet50 | 0.3446 / 0.1504 | 0.3127 / 0.1359 | 0.2873 / 0.1251 | 83.79 / 191.24 | 7 |

## Test per-class AP

Each entry is `mAP50 / mAP50:95`.

| Candidate | EDS panel | Number | Route / landmark | Destination |
|---|---|---|---|---|
| YOLO11n | 0.7088 / 0.3928 | 0.8356 / 0.5593 | 0.6677 / 0.3455 | 0.6539 / 0.3578 |
| **YOLO11s** | **0.8478 / 0.3865** | 0.7950 / **0.5704** | 0.6310 / **0.3476** | 0.5573 / 0.2706 |
| DETR-ResNet50 | 0.5560 / 0.2707 | 0.3446 / 0.1508 | 0.1168 / 0.0347 | 0.1317 / 0.0441 |

## Selection

YOLO11s is selected because it had the highest validation mAP50:95 (`0.4274`). The validation threshold sweep selected confidence `0.20` by F1 (`0.7032`) with zero false positives across four reviewed validation negatives. NMS IoU remained `0.70`.

Selected checkpoint SHA-256: `01d832cb6eda71dcf4a88e6ebbafc080f9dc299be8161c76ab15c75f7c60c2e3`.

## Test execution deviation

The final notebook execution evaluated all three candidates with `OPERATING_CONF=0.30`, rather than evaluating only selected YOLO11s at the validation-selected `0.20`. The test mAP calculation used predictions from score `0.001`; negative false-positive counts were measured at `0.30`. Model selection remains based on validation. Do not use these test results to reselect the model or tune settings, and do not rerun the test to optimize them.

## Findings and remaining evidence

- YOLO11s has the strongest validation AP and lowest median test latency.
- Number detection is its strongest localized class.
- A validation-only review of the ten highest-priority YOLO11s cases found that small/distant text is the dominant miss condition: 52 of 61 GT boxes in those cases occupy less than 1% of the image and 36 occupy less than 0.25%.
- Route/destination separation is the clearest class problem. Diagnostic matching found 17 destination-to-route and 10 route-to-destination confusion candidates across validation.
- DETR is slower, has substantially lower AP and produced seven predictions on two reviewed test negatives at confidence `0.30`.
- The test set is small: 20 images with only two reviewed negatives.
- Blur, glare, oblique perspective, crowding and partial occlusion make several detected crops unsuitable for reliable OCR; the ten-case review, overlays and crops are saved under `yolo11s/qualitative_validation/`.
- The Task 3 semantic audit covers 137 original training, 39 validation and 20 test images. It flags 15 images with 17 panel-without-content cases for joint review and inventories all 22 original zero-box images.
- Twelve timestamp-derived filename groups cross splits, including same-minute screenshot/image sequences. This is evidence of possible shared capture sessions, although only source records can confirm it. Exact/dHash checks alone do not certify recording-level isolation.
- Human confirmation with Jy of class definitions, semantic candidates, negative/Null history, source permissions and capture-group split isolation remains pending; no labels or splits were changed.
- App/OCR integration and camera/uploaded-video testing remain pending.

## Evidence files

- Archived combined validation: `combined_validation.json`
- Archived combined test: `combined_test.json`
- Runtime originals: `.runtime/object_detection_benchmark/bf938f526d2c/runs/baseline-01/benchmark_yolo11n_yolo11s_detr-resnet-50_{validation,test}.json`
- Per-model archived reports: each model's `validation/benchmark.json` and `test/benchmark.json` under this directory
- Selected checkpoint: `.runtime/object_detection_benchmark/bf938f526d2c/runs/baseline-01/yolo11s/weights/best.pt`
- Validation qualitative review: `yolo11s/qualitative_validation/QUALITATIVE_REVIEW.md`
- Machine-readable failure analysis: `yolo11s/qualitative_validation/failure_analysis.json`
- Ten-case contact sheet: `yolo11s/qualitative_validation/contact_sheet.jpg`
- Task 3 joint-review packet: `data_review/REVIEW.md`
- Task 3 machine-readable audit: `data_review/semantic_audit.json`
