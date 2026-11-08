# Reviewed Roboflow v4 detector results

Run `v4-reviewed-01` used the manifest-backed local dataset
`data/training/2026-11-05-roboflow-v4-reviewed/` (manifest SHA-256
`01760a84133353028e203b0f06a4c7dd5d012be7b67c0c02f52fd3e4128180e0`).
The reviewed export has 735 train, 53 validation and 53 test images, including
147, 10 and 12 zero-box images respectively. Its automated audit passed after
removing nine augmented training images from three source families that overlapped
validation or test. Automated checks do not certify every class or box decision.

## Training and validation

All three models started from published pretrained weights, used the same
four-class dataset, seed 42, 640-pixel input, batch size 4 and CUDA. Training was
configured for up to 60 epochs. YOLO11n recorded 52 epochs under patience 15;
YOLO11s and DETR recorded 60. The YOLO runs used full fine-tuning, mosaic 0,
box gain 7.5 and class gain 0.5. Model settings and training histories are saved
under each model's `train/` directory.

| Model | Train mAP50 / mAP50:95 | Validation mAP50 / mAP50:95 | Validation negative FP at confidence 0.20 | Validation median / p95 ms |
| --- | --- | --- | ---: | --- |
| YOLO11n | 0.8807 / 0.7241 | 0.6250 / 0.3383 | 3 | 28.48 / 38.50 |
| **YOLO11s** | **0.8837 / 0.7605** | 0.6131 / **0.3510** | **0** | **26.60 / 34.55** |
| DETR-ResNet50 | 0.5647 / 0.2674 | 0.4377 / 0.1746 | 19 | 63.23 / 81.40 |

Validation per-class AP is shown as `mAP50 / mAP50:95`:

| Model | EDS panel | Number | Route / landmark | Destination |
| --- | --- | --- | --- | --- |
| YOLO11n | 0.7940 / 0.4261 | 0.7252 / 0.4793 | 0.4597 / 0.1747 | 0.5210 / 0.2730 |
| YOLO11s | 0.7843 / 0.4343 | 0.7064 / 0.4891 | 0.4598 / 0.2156 | 0.5020 / 0.2651 |
| DETR-ResNet50 | 0.7831 / 0.3579 | 0.6408 / 0.2504 | 0.0943 / 0.0280 | 0.2325 / 0.0621 |

YOLO11s was selected because it had the highest validation mAP50:95 (`0.3510`).
Its five-point validation confidence sweep had the highest IoU50 F1 at `0.50`
(`0.6877`) with zero false positives on ten validation negatives. Confidence
`0.10` had nearly the same F1 (`0.6868`) and higher recall (`0.6697` versus
`0.5928`). The final test used `0.50`, with NMS IoU `0.70` retained. The NMS
setting was not separately swept.

After the recorded final test, a **validation-only exploratory NMS comparison**
was run on the same saved YOLO11s checkpoint. NMS `0.50` gave mAP50:95 `0.3532`
and diagnostic IoU50 F1 `0.6933`; NMS `0.70` gave `0.3510` and `0.6877`.
Both had zero predictions on ten validation negatives at confidence `0.50`.
The small difference does not change the recorded final-test configuration:
that result belongs to NMS `0.70`. See the [validation review](validation_review/REVIEW.md)
for error counts, overlays and limits.

## Final held-out test

Only the validation-selected YOLO11s was tested. The test included 53 images,
12 of them zero-box negatives.

| Model | Test mAP50 | Test mAP50:95 | Negative FP at confidence 0.50 | Median / p95 ms |
| --- | ---: | ---: | ---: | --- |
| YOLO11s | 0.6314 | 0.3270 | 1 | 26.46 / 36.57 |

| Test class | mAP50 | mAP50:95 |
| --- | ---: | ---: |
| EDS panel | 0.7467 | 0.3158 |
| Number | 0.7934 | 0.5246 |
| Route / landmark | 0.4116 | 0.2027 |
| Destination | 0.5739 | 0.2651 |

Selected YOLO11s `best.pt` SHA-256:
`97150601de39a999754015648cad2ef930842d52e8e37eb77d7576ffe2da33b5`.
The checkpoint is a local ignored artifact, not part of the Git commit. Keep a
separate backup before moving machines; the previous `baseline-01` weights are
still present and unchanged.

The [v4 detector configuration](detector_config.json) records the tested
confidence `0.50`, NMS `0.70`, class mapping and checkpoint hash. A
[local application-path smoke test](validation_review/integration_verification.json)
loaded the installed default checkpoint, associated fields and produced
nonempty crops on two validation images; a validation negative produced no
detection. The app now defaults to v4 at confidence `0.50` and NMS `0.70`.
The baseline checkpoint and reports are retained. This is not OCR or field-video
verification.

## Interpretation and remaining review

- Number has the strongest test localization AP; route is the weakest. The
  validation-to-test change is small in aggregate, but the test has only 53
  images and does not establish deployment performance.
- The new validation mAP50:95 (`0.3510`) is below the old `baseline-01`
  validation score (`0.4274`). The datasets and split sizes differ, so this
  comparison alone does not measure the causal effect of the new images or 60
  epochs. It does not support a claim that mAP increased.
- Per-image bus type, lighting, angle, distance, blur and occlusion tags have
  not been reviewed across the full split. The twelve visually inspected
  high-priority cases in the validation review indicate difficult small/distant,
  angled and nested-text conditions, but do not establish category-level rates.
- The source export's automated cleanup removed known similar-scene overlaps;
  source/capture provenance, negative semantics and full four-class annotation
  completeness still require human confirmation with Jy. This review is on hold
  at Brendan's request.
- Keep the final test closed for tuning. Future changes should use validation
  and a new run ID, preserving this result as recorded evidence.

## Saved evidence

The [OCR crop handoff](OCR_HANDOFF.md) documents the committed validation
annotation and predicted-box crops for Cody.

- Combined validation:
  `.runtime/object_detection_benchmark/01760a841333/runs/v4-reviewed-01/benchmark_yolo11n_yolo11s_detr-resnet-50_validation.json`
- Combined selected-model test:
  `.runtime/object_detection_benchmark/01760a841333/runs/v4-reviewed-01/benchmark_yolo11s_test.json`
- Git-trackable per-model reports: each model's `validation/benchmark.json` and
  YOLO11s `test/benchmark.json` alongside this file.
- Training histories/settings: `train/results.csv`, `train/args.yaml` and
  `train/results.png` for YOLO; `train/history.json` for DETR; `status.json` for
  each model. Model weight files under `checkpoints/` are Git-ignored.
