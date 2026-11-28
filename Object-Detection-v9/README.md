# Object detection v9: local runs

This directory holds the completed local detector experiment on
`data/training/2026-11-25-roboflow-v9-stem-isolated/`. It uses the same
`object_detection/<dataset-fingerprint>/runs/<run-id>/` layout as the historical
[`Object-Detection-v4`](../Object-Detection-v4/README.md)
archive. Read [RESULTS.md](RESULTS.md) for the seven-model validation comparison,
the selected-model final test, and links to every benchmark report. The v4 OCR
handoff and deployed detector are separate.

The [benchmark notebook](../notebooks/object_detection_benchmark.ipynb) sets both
`EDS_OUTPUT_ROOT` and `EDS_ARCHIVE_ROOT` to this directory's
`object_detection/` subfolder. The standalone trainer uses the same local paths
when given the named v9 dataset, even from a new PowerShell session. Training
histories, benchmarks, split tables, and checkpoints are saved here. Published
starting weights and the generated YOLO dataset view stay under ignored
`.runtime/object_detection_benchmark/`.

Saved structure (fingerprint prefix `43159c679cbe`):

```text
Object-Detection-v9/
  object_detection/
    <dataset-fingerprint>/
      runs/
        v9-local-01/
          yolo11n/                  # Also yolo11s and detr-resnet-50
            results.csv             # YOLO epoch log
            args.yaml               # YOLO settings
            weights/best.pt         # Best checkpoint from training
            weights/last.pt         # Last checkpoint from training
            complete.txt            # Written only after successful training
            train/                  # Mirrored training evidence
            validation/benchmark.json
            checkpoints/            # Copies of selected training weights
            status.json
          benchmark_*_validation.json
          benchmark_*_validation_tables.md
          benchmark_*_test.json
          benchmark_*_test_tables.md
        v9-tuning-01/
          yolo11s-gentle_aug/      # Selected A variant; three other A/B runs alongside it
            weights/best.pt
            test/benchmark.json    # Selected model only
```

DETR writes its model and processor files at the model run root and mirrors the
best model into `checkpoints/`. The trainer backs up YOLO `best.pt` and `last.pt`
separately under [`YOLO_Weights/v9/`](../YOLO_Weights/v9/README.md)
at `<dataset-fingerprint>/runs/<run-id>/<model>/`. On a normal interruption,
it also mirrors any epoch log and weights already saved, marked `partial`.
The combined final-test report and tables are under `v9-local-01/`; the
selected model's per-model test copy is under `v9-tuning-01/`. Other candidates
received validation only. A model run is complete only when `complete.txt`
exists; `status.json` records which evaluation phases are saved.

Keep one baseline run ID for models that belong to the same new comparison set.
Choose a new ID for any model whose folder already exists, including a partial
run; the training script refuses to replace an existing model run.
See the [notebook instructions](../notebooks/README.md) for the manual sequence.

## V9 baseline settings

Compared with the reviewed-v4 training, the requested changes are batch size
`32` and four training data-loading workers. YOLO11n and YOLO11s use a physical
batch of 32. DETR uses two images per GPU microbatch and accumulates gradients
over 16 microbatches for an effective batch of 32. This accumulation is a
memory-aware approximation of a physical 32-image DETR step. The remaining
settings stay at 60 epochs, 640-pixel input, seed 42, and the v4 training
configuration. The selected v9 final test used validation-chosen confidence
`0.50` and NMS IoU `0.70`.

## Optional YOLO A/B runs

Notebook section 3B records the four completed YOLO11n/s experiments in the
[tuning plan](../docs/OBJECT_DETECTION_YOLO_TUNING_PLAN.md). A (`gentle_aug`)
uses input 640, translation 0.02, scale 0.10, and brightness variation 0.08.
B (`localization`) uses input 800 and box-loss gain 8.5. Both start from the
published model weight and keep baseline checkpoints intact. Each variant is
saved under `object_detection/<fingerprint>/runs/<tuning-run-id>/` with names
such as `yolo11s-localization`; its `args.yaml`, `results.csv`,
`experiment.json`, and `weights/` are separate. YOLO backups use the same
variant name under `YOLO_Weights/v9/`. The common notebook benchmark can read
completed variants at their recorded input sizes. Both B runs used batch 16
at 800 pixels; their baselines and A runs used batch 32 at 640 pixels. See
[RESULTS.md](RESULTS.md) for measured outcomes and remaining review work.
