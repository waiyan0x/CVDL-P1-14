# Object detection run archive

## Current handoff

`bf938f526d2c/runs/baseline-01/` is the completed three-model benchmark. YOLO11s
was selected using validation mAP50:95, and the held-out test has already been
run. Do not overwrite, delete or retune this run using its test results. Start
with [RESULTS.md](bf938f526d2c/runs/baseline-01/RESULTS.md) and the repository
[object-detection handoff](../../docs/OBJECT_DETECTION_HANDOFF.md).

The remaining detector decisions are the joint Jy/Brendan annotation and split
review plus, if required by the allocation, a validation-only comparison of NMS
IoU settings. Any label or split change requires a new manifest, dataset version
and run ID. If nothing changes, the existing benchmark should not be rerun.

Each dataset manifest gets a directory named by the first 12 characters of its SHA-256 fingerprint. Fresh experiments use `runs/<RUN_ID>/<model>/`, each with `train/`, `validation/`, `test/`, and `checkpoints/` folders. `status.json` identifies completed, partial, and pending results.

The notebook writes per-model benchmark JSON files here after evaluation. YOLO training CSV, run settings, plots, and copies of `best.pt` and `last.pt` are mirrored here as well. DETR writes loss history after each epoch and mirrors its best checkpoint. Benchmark reports are created only when measured; no pending scores are filled in.

Metric files are Git-trackable. Model weights in `checkpoints/` are ignored because they can be large. Keep a separate backup of the whole `evaluation/object_detection/` directory if you need the weights beyond this computer. The source dataset remains under ignored `data/training/`.

To refresh the archive from local YOLO runs without training, run `venv\detector\Scripts\python.exe scripts\sync_object_detection_artifacts.py` from the repository root.

Fresh training starts from the pretrained YOLO11 or DETR model under the command's
`--run-id`. Change the ID for a new attempt of the same model. An existing run
folder causes an error. New checkpoints are saved because validation and test
require the trained model, but training never resumes from them. Generated model
weights are ignored by Git, so transfer or back them up separately when handing
the run to another machine.
