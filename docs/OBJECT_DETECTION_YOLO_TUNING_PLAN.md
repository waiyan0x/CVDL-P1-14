# YOLO11n and YOLO11s v9 tuning plan

This is a plan for four **proposed** experiments: A and B for YOLO11n, and A and B for YOLO11s. They are separate fresh fine-tuning runs, not continuations of the baseline checkpoints. No A/B validation or test result is claimed here. The three-model baseline and the four YOLO variants make seven candidates in total; DETR has no A/B variant in this plan.

## Dataset and decision boundary

Use only the verified `data/training/2026-11-25-roboflow-v9-stem-isolated/` export: 6,858 training, 294 validation, and 299 held-out test images. Its four foreground classes are `front_eds` (whole panel), `front_eds_num` (service number), `front_eds_route` (route or landmark text), and `front_eds_destination` (destination). The training split already contains saved augmented images, so additional transforms may be redundant. The automated split and integrity audit passed; human source-scene and annotation review remains open. If review changes labels or split membership, make a new dataset version and compare all candidates on that version.

The earlier v9 Colab histories are **historical diagnostics**, not the baseline for this plan. Compare A/B only with the new local YOLO11n and YOLO11s baselines trained on the same verified export. Do not fill in scores from the old runs or treat a partial epoch log as a completed baseline.

Complete the three local baselines (YOLO11n, YOLO11s, DETR), then train the four YOLO variants. Benchmark all seven on the **same validation split**. Select the final model and inference settings using validation only, then run the held-out test once on the selected model. The test set must not decide whether A or B is kept.

## Controls shared by both YOLO models

Each run starts from its own published COCO-pretrained weight (`yolo11n.pt` or `yolo11s.pt`), updates the full network, uses seed `42`, a 60-epoch cap, and patience `15`. Keep the same four classes, verified dataset, optimizer choice, and training code version. The current baseline trainer uses deterministic training, Ultralytics optimizer `auto`, `box=7.5`, `cls=0.5`, `dfl=1.5`, and zero mosaic, MixUp, copy-paste, rotation, translation, scaling, horizontal flip, hue change, and saturation change. Keep those baseline choices except for the values explicitly changed below. In particular, horizontal flips can reverse bus sign text and are excluded.

Choose a batch size that fits the local GPU **before** comparing variants. Record the actual batch, GPU, training time, and Ultralytics version in every run. Keep the baseline and A batch equal for a given model. Try to keep B equal too; if 800-pixel images require a smaller batch, record it as an additional difference. Do not assume the previous Colab batch sizes of 32 and 16 will fit the local GPU. Worker count, image cache, and mixed precision can change throughput, but keep them consistent across a model's baseline and variants when possible. Do not alter validation or test images.

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
| Batch | measured local fit | same as baseline | same if it fits |

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
| Batch | measured local fit | same as baseline | same if it fits |

## YOLO11s A: gentle scene variation

**Question:** Can moderate training-time variation improve YOLO11s generalization to different bus scenes and lighting?

Use the same A settings as YOLO11n: `translate=0.02`, `scale=0.10`, and `hsv_v=0.08` at `imgsz=640`. Keeping the intervention identical makes the n and s responses easier to compare. The larger model may learn these variations more effectively, but extra augmentation may be redundant with the saved v9 variants or distort tiny signs. Keep mosaic and flips disabled to preserve the relationships between a panel and its nested text boxes.

## YOLO11s B: higher-resolution localization

**Question:** Will more image detail and stronger box supervision improve YOLO11s placement of the nested EDS fields?

Use `imgsz=800` and `box=8.5`, with A transforms off. The motivation is the same small and tightly bounded fields as for YOLO11n. At 800 pixels, both training and intended inference cost more. Evaluate B at 800 for its intended quality and latency; do not report a 640-pixel latency as if it were B's deployed setting. Inaccurate annotation edges may limit or reverse any benefit from a larger box-loss weight.

## Validation and reporting

For each baseline and variant, retain `args.yaml`, epoch `results.csv`, `weights/best.pt`, `weights/last.pt`, the best epoch, and the dataset manifest hash. Compare best-checkpoint validation mAP50–95 and mAP50 **per class**, especially `front_eds_num`, `front_eds_route`, and `front_eds_destination`. Also inspect false positives on reviewed zero-box validation images, missed small signs, duplicate or misassigned nested boxes, OCR crop quality, and inference time on the same hardware. Keep the inference confidence/NMS policy consistent for like-for-like comparisons; choose any operating threshold using validation only. The notebook currently starts at the v4 operating confidence `0.50` and NMS IoU `0.70`.

Give each variant a distinct model/run directory, such as `v9-tuning-01/yolo11n-gentle_aug`, `v9-tuning-01/yolo11n-localization`, `v9-tuning-01/yolo11s-gentle_aug`, and `v9-tuning-01/yolo11s-localization`, under `Object-Detection-v9/object_detection/<dataset-fingerprint>/runs/`. Keep the baseline folders intact, including a partial or restarted run under another ID, and use separate YOLO weight backups. A complete common benchmark must load these four variant checkpoints explicitly; baseline-only benchmark results do not evaluate them.

**Notebook controls:** in the first code cell, set `RUN_TRAINING=False`, `RUN_TUNING=True`, `TUNING_MODEL` to `yolo11n` or `yolo11s`, and `TUNING_VARIANT` to `gentle_aug` (A) or `localization` (B). Keep `RUN_BENCHMARK=False` and `RUN_FINAL_TEST=False`. Set `RUN_ID` to the completed baseline's ID and `TUNING_RUN_ID` to a distinct ID for all four variants. Run All once per variant. The tuning cell requires that model's baseline `complete.txt` and refuses an existing variant folder. B uses input 800 automatically. Set `TUNING_BATCH_SIZE` before each run, and record any reduction from its baseline batch due to GPU memory.

**Common benchmark:** after training, set `RUN_TUNING=False`, `RUN_BENCHMARK=True`, and list completed baseline and A/B names in `BENCHMARK_MODELS`. If a baseline has a different run ID from `RUN_ID`, map it in `BENCHMARK_MODEL_RUNS`, for example `{'detr-resnet-50': 'v9-local-02'}`. The evaluator reads each YOLO candidate's saved `args.yaml` input size, including 800 for B; results and tables are written to `Object-Detection-v9`. Use `RUN_FINAL_TEST=True` only for the validation-selected candidate after all settings are frozen. The notebook starts with tuning and benchmarking disabled, and this document does not claim that any A/B run has happened.

Parameter definitions: [Ultralytics training settings](https://docs.ultralytics.com/modes/train) and [augmentation guide](https://docs.ultralytics.com/guides/yolo-data-augmentation).
