# YOLO11n and YOLO11s v9 A/B experiments

Four A/B experiments completed: A and B for YOLO11n and YOLO11s. Each was a fresh fine-tuning run from published weights, separate from its baseline checkpoint. The seven-candidate validation comparison selected YOLO11s-A; only that candidate received a held-out test. See the [measured v9 results](../Object-Detection-v9/RESULTS.md). DETR had no A/B variant.

## Dataset and decision boundary

Use only the verified `data/training/2026-11-25-roboflow-v9-stem-isolated/` export: 6,858 training, 294 validation, and 299 held-out test images. Its four foreground classes are `front_eds` (whole panel), `front_eds_num` (service number), `front_eds_route` (route or landmark text), and `front_eds_destination` (destination). The training split already contains saved augmented images, so additional transforms may be redundant. The automated split and integrity audit passed; human source-scene and annotation review remains open. If review changes labels or split membership, make a new dataset version and compare all candidates on that version.

Earlier v9 Colab histories are historical diagnostics. The reported A/B comparison uses the completed local baselines and the same verified v9 export. Partial epoch logs are not treated as completed models.

The three local baselines and four variants completed. Validation selected the model and operating threshold before one selected-model held-out test. The test set was not used to decide whether A or B was kept.

## Controls shared by both YOLO models

Each run starts from its own published COCO-pretrained weight (`yolo11n.pt` or `yolo11s.pt`), updates the full network, uses seed `42`, a 60-epoch cap, and patience `15`. Keep the same four classes, verified dataset, optimizer choice, and training code version. The current baseline trainer uses deterministic training, Ultralytics optimizer `auto`, `box=7.5`, `cls=0.5`, `dfl=1.5`, and zero mosaic, MixUp, copy-paste, rotation, translation, scaling, horizontal flip, hue change, and saturation change. Keep those baseline choices except for the values explicitly changed below. In particular, horizontal flips can reverse bus sign text and are excluded.

The local baselines and A used batch 32 at 640 pixels; both B runs used batch 16 at 800 pixels to fit the GPU. This batch difference is part of the B comparison. Each run retains its actual settings in `args.yaml`; validation and test images were unchanged.

The loss gains are training weights, not confidence or NMS thresholds. A and B test **different hypotheses**; neither combines the other's changes. B changes resolution and box-loss gain together, so a gain would support the package, not prove which of those two changes caused it. A follow-up ablation would be needed to separate them.

## YOLO11n settings

| Setting | Baseline | A: gentle variation | B: localization |
| --- | ---: | ---: | ---: |
| Published starting weights | `yolo11n.pt` | `yolo11n.pt` | `yolo11n.pt` |
| `imgsz` | 640 | 640 | **800** |
| `translate` | 0 | **0.02** | 0 |
| `scale` | 0 | **0.10** | 0 |
| `hsv_v` | 0 | **0.08** | 0 |
| `box` loss gain | 7.5 | 7.5 | **8.5** |
| `cls`, `dfl` gains | 0.5, 1.5 | 0.5, 1.5 | 0.5, 1.5 |
| Batch | 32 | 32 | 16 |

## YOLO11n A: gentle scene variation

**Question:** Can the smaller network generalize better across nearby camera framing, viewing distance, and illumination without losing the thin LED characters?

Use `translate=0.02`, `scale=0.10`, and `hsv_v=0.08` at `imgsz=640`; keep the other baseline settings. A two-percent translation is about 13 pixels at this input size, while scale and brightness changes remain modest. These transforms act on training images and update their boxes; they do not create new files or touch validation/test. This is relevant to buses photographed at slightly different angles, distances, and lighting. Because v9 already contains saved augmentation, A could also add unrealistic variation or suppress small text. Judge it from validation, not from the training loss alone.

## YOLO11n B: small-field localization

**Question:** Does retaining more pixels and emphasizing box placement help YOLO11n locate service numbers, route text, and destinations more tightly?

Use `imgsz=800` and `box=8.5`, with no added A transforms. Going from 640 to 800 increases each side by 25% and total input pixels by 56.25%. The box gain rises about 13.3% from 7.5. The compact YOLO11n may benefit from clearer small fields, but it may also lack capacity to use the extra detail, run slower, or overfit imperfect boxes. Measure inference latency and OCR crop usability alongside AP. Lower the batch only if the 800-pixel run does not fit, and record that deviation.

## YOLO11s settings

| Setting | Baseline | A: gentle variation | B: localization |
| --- | ---: | ---: | ---: |
| Published starting weights | `yolo11s.pt` | `yolo11s.pt` | `yolo11s.pt` |
| `imgsz` | 640 | 640 | **800** |
| `translate` | 0 | **0.02** | 0 |
| `scale` | 0 | **0.10** | 0 |
| `hsv_v` | 0 | **0.08** | 0 |
| `box` loss gain | 7.5 | 7.5 | **8.5** |
| `cls`, `dfl` gains | 0.5, 1.5 | 0.5, 1.5 | 0.5, 1.5 |
| Batch | 32 | 32 | 16 |

## YOLO11s A: gentle scene variation

**Question:** Can moderate training-time variation improve YOLO11s generalization to different bus scenes and lighting?

Use the same A settings as YOLO11n: `translate=0.02`, `scale=0.10`, and `hsv_v=0.08` at `imgsz=640`. Keeping the intervention identical makes the n and s responses easier to compare. The larger model may learn these variations more effectively, but extra augmentation may be redundant with the saved v9 variants or distort tiny signs. Keep mosaic and flips disabled to preserve the relationships between a panel and its nested text boxes.

## YOLO11s B: higher-resolution localization

**Question:** Will more image detail and stronger box supervision improve YOLO11s placement of the nested EDS fields?

Use `imgsz=800` and `box=8.5`, with A transforms off. The motivation is the same small and tightly bounded fields as for YOLO11n. At 800 pixels, both training and intended inference cost more. Evaluate B at 800 for its intended quality and latency; do not report a 640-pixel latency as if it were B's deployed setting. Inaccurate annotation edges may limit or reverse any benefit from a larger box-loss weight.

## Validation and reporting

For each baseline and variant, retain `args.yaml`, epoch `results.csv`, `weights/best.pt`, `weights/last.pt`, the best epoch, and the dataset manifest hash. Compare best-checkpoint validation mAP50–95 and mAP50 **per class**, especially `front_eds_num`, `front_eds_route`, and `front_eds_destination`. Also inspect false positives on reviewed zero-box validation images, missed small signs, duplicate or misassigned nested boxes, OCR crop quality, and inference time on the same hardware. Keep the inference confidence/NMS policy consistent for like-for-like comparisons; choose any operating threshold using validation only. The notebook currently starts at the v4 operating confidence `0.50` and NMS IoU `0.70`.

The four variant folders are `v9-tuning-01/yolo11n-gentle_aug`, `v9-tuning-01/yolo11n-localization`, `v9-tuning-01/yolo11s-gentle_aug`, and `v9-tuning-01/yolo11s-localization` under `Object-Detection-v9/object_detection/43159c679cbe/runs/`. Each has its own checkpoint and YOLO weight backup. Baselines remain under `v9-local-01/`. The [common validation report](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11n_yolo11s_yolo11n-gentle_aug_yolo11n-localization_yolo11s-gentle_aug_yolo11s-localization_validation.json) includes all six YOLO candidates; the separate baseline report includes DETR.

**Notebook controls for a new experiment:** keep all switches off when reviewing saved outputs. To train another variant, use a new `TUNING_RUN_ID`, set `RUN_TUNING=True`, and select `TUNING_MODEL` and `TUNING_VARIANT` in the first code cell. The tuning cell requires a completed baseline and refuses an existing variant folder. B uses input 800; set its batch before starting.

**Recorded outcome:** YOLO11s-A led validation mAP50:95 at `68.4%` and scored `68.2%` on the one held-out test. YOLO11n-B had fewer negative-image validation detections (3 versus 13), which remains a deployment tradeoff. The [final-test report](../Object-Detection-v9/object_detection/43159c679cbe/runs/v9-local-01/benchmark_yolo11s-gentle_aug_test.json) contains the full train/validation/test metrics; do not rerun the test to tune the choice.

Parameter definitions: [Ultralytics training settings](https://docs.ultralytics.com/modes/train) and [augmentation guide](https://docs.ultralytics.com/guides/yolo-data-augmentation).
