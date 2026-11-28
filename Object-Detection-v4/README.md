# Historical v4 object detection archive

This folder preserves the detector work before the [v9 experiment](../Object-Detection-v9/RESULTS.md).
The two v4 datasets and their held-out tests remain separate from v9.

| V4 run | Purpose | Validation mAP50:95 | Final test mAP50:95 |
| --- | --- | ---: | ---: |
| [Earlier baseline](object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md) | First three-model comparison | 42.7% for selected YOLO11s | See run report |
| [Reviewed Roboflow v4](object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md) | Corrected four-class export and deployed YOLO11s | 35.1% | 32.7% |

The [object detection directory](object_detection/README.md) holds per-model
settings, training histories, validation reports, checkpoints, and v4 reviews.
The [reviewed-v4 OCR package](ocr_handoff/v4-reviewed-01/README.md) contains the
source COCO photos, class crops, transcription templates, and detector checkpoint
in one Git LFS ZIP. The [v4 weight backup](../YOLO_Weights/v4-baseline/README.md)
is separate from the [v9 backups](../YOLO_Weights/v9/README.md).

The application still uses the reviewed-v4 checkpoint. The v9 results are
research measurements and do not replace the application model. This archive
does not change the active notebook or its v9 output directory.
