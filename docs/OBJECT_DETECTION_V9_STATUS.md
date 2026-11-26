# Object detection v9 status (26 November 2026)

This page records the v9 detector continuation. The deployed detector remains
the reviewed-v4 YOLO11s described in [the detector handoff](OBJECT_DETECTION_HANDOFF.md).
V9 is a separate experiment; its validation and held-out test results must not
be mixed with v4 results.

## Dataset and provenance

The raw Roboflow `data/training/Front EDS.v9i.coco/` export lists 7,272 train,
303 validation and 303 test images. The prepared
`data/training/2026-11-25-roboflow-v9-stem-isolated/` copy lists **6,858 train,
294 validation and 299 test** images. Its `preparation_manifest.json` SHA-256 is
`43159c679cbe4ea7d3b791ef106d66ce7795a10307155fbc33863205868198d7`.
The 427 exclusions and source-stem rules are recorded in
`split_isolation_audit.json`. The retained annotations were not rewritten.

The extracted folders are ignored by Git. The corrected v9 ZIP at
`data/training/2026-11-25-roboflow-v9-stem-isolated.zip` is tracked with Git
LFS; its SHA-256 is
`19a5cdb1eea146b4817ed12287103a25e76224f8819c3130ed5dc629b042218a`.
Run `python scripts/verify_v9_object_detection_export.py` after extracting
it. The raw export and synthetic v5 data are not in that ZIP. Filename-stem and
checksum checks cannot establish independence between differently named photos
or completeness of every EDS box; human scene and annotation review remains open.

## Training and measured evidence

The notebook uses four classes: `front_eds`, `front_eds_num`, `front_eds_route`
and `front_eds_destination`. The planned comparison uses 640-pixel input,
seed 42 and up to 60 epochs per model. The Colab run ID is
`v9-2026-11-25-01`; its outputs go under
`MyDrive/CVDL-P1-14-colab/results/`.

The Colab YOLO training CSVs viewed during the session gave these **best
per-epoch Ultralytics validation figures**. The original v9 CSVs and model
checkpoints have not yet been copied into this repository, so these figures
are session notes, not an archived common benchmark:

| Model | Best epoch in viewed CSV | Validation mAP50 | Validation mAP50:95 |
| --- | ---: | ---: | ---: |
| YOLO11n | 8 | 0.92966 | 0.67547 |
| YOLO11s | 9 | 0.93337 | 0.69106 |

The user reports that both YOLO run folders now contain `complete.txt` and
`weights/best.pt` on Google Drive. YOLO11s was previously interrupted after
epoch 34 and resumed; obtain its final `results.csv`, checkpoint hashes and
completion marker from Drive before publishing a final run summary. No v9
DETR mAP has been measured. The current DETR trainer saves its best model and
loss history each epoch but has no optimizer/epoch resume checkpoint. A paused
Colab process can continue only while the same runtime survives.

**As of this repository snapshot, no common v9 YOLO11n-versus-YOLO11s
benchmark JSON or v9 held-out test JSON is archived here.** Do not substitute
the training CSV figures for a common benchmark or invent DETR scores. The
historical v4 DETR validation mAP50/mAP50:95 was `0.4377/0.1746` on a different
dataset; see [the v4 results](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md).

## Next evaluation steps

Use [the benchmark notebook](../notebooks/object_detection_benchmark.ipynb)
on a Colab GPU with the corrected v9 dataset and saved model folders. First
compare the completed YOLO checkpoints on train and validation:

```python
RUN_TRAINING = False
RUN_BENCHMARK = True
RUN_FINAL_TEST = False
RUN_ID = 'v9-2026-11-25-01'
BENCHMARK_MODELS = ('yolo11n', 'yolo11s')
```

Inspect validation mAP50:95 by class, negative-image false positives and the
threshold sweep; choose one model and an operating confidence threshold from
validation. Keep NMS IoU `0.70` unless a new validation comparison justifies a
change. Then set `RUN_FINAL_TEST=True`, leave `RUN_BENCHMARK=True`, and set
`BENCHMARK_MODELS` to a one-item tuple containing the chosen model. Run the
299-image held-out test once. The current notebook reevaluates train and
validation during that final pass.

The notebook requires `weights/best.pt` and `complete.txt` for a normal
completed YOLO run. If a partial checkpoint must be evaluated, record its
actual epoch and partial status explicitly; do not create a false completion
marker. Benchmark JSON and separate split tables save under the Drive run
directory, while per-model archives save under the Drive
`Obj-Dect-OCR/object_detection/43159c679cbe/runs/v9-2026-11-25-01/` tree.
These Drive files do not sync into this Git checkout automatically. Copy and
verify the original reports and selected checkpoints before committing any
v9 result or changing the application's deployed model.
