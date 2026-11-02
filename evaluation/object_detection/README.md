# Object detection run archive

Each dataset manifest gets a directory named by the first 12 characters of its SHA-256 fingerprint. Within it, each model has `train/`, `validation/`, `test/`, and `checkpoints/` folders. `status.json` identifies completed, partial, and pending results.

The notebook writes per-model benchmark JSON files here after evaluation. YOLO training CSV, run settings, plots, and copies of `best.pt` and `last.pt` are mirrored here as well. DETR writes loss history after each epoch and mirrors its best checkpoint. Benchmark reports are created only when measured; no pending scores are filled in.

Metric files are Git-trackable. Model weights in `checkpoints/` are ignored because they can be large. Keep a separate backup of the whole `evaluation/object_detection/` directory if you need the weights beyond this computer. The source dataset remains under ignored `data/training/`.

To refresh the archive from local YOLO runs without training, run `venv\detector\Scripts\python.exe scripts\sync_object_detection_artifacts.py` from the repository root. This preserves completed and interrupted runs.
