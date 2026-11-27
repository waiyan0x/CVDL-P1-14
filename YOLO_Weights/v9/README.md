# V9 YOLO weight backups

Fresh v9 YOLO11n and YOLO11s runs copy their `best.pt` and `last.pt` here under
`<dataset-fingerprint>/runs/<run-id>/<model>/`. This folder is separate from the
existing root-level `YOLO_Weights/yolo11n.pt` and
`YOLO_Weights/yolo11s-best.pt` files. The original training checkpoints also
remain under `Object-Detection-v9/object_detection/<dataset-fingerprint>/runs/`.

The optional A/B runs use separate model names such as `yolo11n-gentle_aug`
and `yolo11s-localization` under their `TUNING_RUN_ID`. Baseline and variant
weights therefore have separate paths. A weight backup alone is not evidence
of a finished run; check its model folder's `complete.txt` and `status.json`.
New `.pt` files in this tree use Git LFS if they are later added to a commit.
