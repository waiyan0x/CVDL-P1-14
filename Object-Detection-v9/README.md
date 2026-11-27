# Object detection v9: local runs

This directory is reserved for fresh local training on
`data/training/2026-11-25-roboflow-v9-stem-isolated/`. It uses the same
`object_detection/<dataset-fingerprint>/runs/<run-id>/` layout as the historical
[`Object-Detection-v4`](../Object-Detection-v4/object_detection/README.md)
archive. It does not contain the v4 OCR handoff. The v9 folder starts with no
measured results or checkpoints.

The [benchmark notebook](../notebooks/object_detection_benchmark.ipynb) sets both
`EDS_OUTPUT_ROOT` and `EDS_ARCHIVE_ROOT` to this directory's
`object_detection/` subfolder. The standalone trainer uses the same local paths
when given the named v9 dataset, even from a new PowerShell session. Raw YOLO training files, validation and test
benchmarks, split tables, and copied checkpoints therefore stay together on this
computer. Starting YOLO weights and the generated YOLO dataset view stay under
ignored `.runtime/object_detection_benchmark/`.

Expected structure after a run:

```text
Object-Detection-v9/
  object_detection/
    <dataset-fingerprint>/
      runs/
        v9-local-01/
          yolo11n/                  # One model per folder; likewise yolo11s, detr-resnet-50
            results.csv             # YOLO epoch log
            args.yaml               # YOLO settings
            weights/best.pt         # Best checkpoint from training
            weights/last.pt         # Last checkpoint from training
            complete.txt            # Written only after successful training
            train/                  # Mirrored training evidence
            validation/benchmark.json
            test/benchmark.json     # Only after the final held-out test
            checkpoints/            # Copies of selected training weights
            status.json
          benchmark_*_validation.json
          benchmark_*_validation_tables.md
          benchmark_*_test.json
          benchmark_*_test_tables.md
```

DETR writes its model and processor files at the model run root and mirrors the
best model into `checkpoints/`. The trainer backs up YOLO `best.pt` and `last.pt`
separately under [`YOLO_Weights/v9/`](../YOLO_Weights/v9/README.md)
at `<dataset-fingerprint>/runs/<run-id>/<model>/`. On a normal interruption,
it also mirrors any epoch log and weights already saved, marked `partial`.
The `test/` and test summary files are created only when final testing is enabled.
Nothing here is a measured result until the corresponding training or evaluation
step completes.

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
configuration. The benchmark starts with the v4 operating confidence `0.50`
and NMS IoU `0.70`; choose any later change on v9 validation only. A run is
complete only when its own `complete.txt` exists; a partial epoch history is
retained as evidence, not a final benchmark result.

## Optional YOLO A/B runs

Notebook section 3B implements the four separate YOLO11n/s experiments in the
[tuning plan](../docs/OBJECT_DETECTION_YOLO_TUNING_PLAN.md). A (`gentle_aug`)
uses input 640, translation 0.02, scale 0.10, and brightness variation 0.08.
B (`localization`) uses input 800 and box-loss gain 8.5. Both start from the
published model weight and keep baseline checkpoints intact. Each variant is
saved under `object_detection/<fingerprint>/runs/<tuning-run-id>/` with names
such as `yolo11s-localization`; its `args.yaml`, `results.csv`,
`experiment.json`, and `weights/` are separate. YOLO backups use the same
variant name under `YOLO_Weights/v9/`. The common notebook benchmark can read
completed variants at their recorded input sizes. No A/B result is implied by
this setup.
