# Object detection v9: local runs

This directory is reserved for fresh local training on
`data/training/2026-11-25-roboflow-v9-stem-isolated/`. It uses the same
`object_detection/<dataset-fingerprint>/runs/<run-id>/` layout as the historical
[`Object-Detection-v4`](../Object-Detection-v4/object_detection/README.md)
archive. It does not contain the v4 OCR handoff. The v9 folder starts with no
measured results or checkpoints.

The [benchmark notebook](../notebooks/object_detection_benchmark.ipynb) sets both
`EDS_OUTPUT_ROOT` and `EDS_ARCHIVE_ROOT` to this directory's
`object_detection/` subfolder. Raw YOLO training files, validation and test
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
best model into `checkpoints/`. The notebook backs up YOLO `best.pt` and `last.pt`
separately under `YOLO_Weights/v9/<dataset-fingerprint>/runs/<run-id>/<model>/`.
The `test/` and test summary files are created only when final testing is enabled.
Nothing here is a measured result until the corresponding training or evaluation
step completes.

Keep `v9-local-01` for the three baseline models. Choose a new run ID for any
later experiment; the training script refuses to replace an existing model run.
See the [notebook instructions](../notebooks/README.md) for the manual sequence.
