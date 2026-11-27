# V9 YOLO weight backups

Fresh v9 YOLO11n and YOLO11s runs copy their `best.pt` and `last.pt` here under
`<dataset-fingerprint>/runs/<run-id>/<model>/`. This folder is separate from the
existing root-level `YOLO_Weights/yolo11n.pt` and
`YOLO_Weights/yolo11s-best.pt` files. The original training checkpoints also
remain under `Object-Detection-v9/object_detection/<dataset-fingerprint>/runs/`.

No v9 weights have been trained or copied yet. New `.pt` files in this tree use
Git LFS if they are later added to a commit.
