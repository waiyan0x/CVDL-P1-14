# OCR handoff: reviewed v4 validation crops

`ground_truth/` contains tight crops from COCO annotations; `predicted/` contains tight crops from the selected YOLO11s detector at confidence 0.50 and NMS IoU 0.70. Each has panel, number, route and destination folders. The panel crop is context; text OCR should primarily use number, route and destination.

`manifest.json` links every crop to its source image, coordinates, class, and prediction confidence. A same-class IoU >= 0.50 match is diagnostic only, not proof of readable or correct text. `transcriptions_template.csv` lists annotation-based text crops and has blank transcription fields: a human must review crops and enter verified text before CER, word error or exact-text accuracy can be reported.

The crop geometry has no padding or resizing. Cody can apply identical preprocessing variants across OCR models. Keep train, validation and held-out test separate; this package uses validation only and is for selection/diagnostics. The detector's final test is closed for tuning.

These validation crops, the manifest and transcription template are committed under `evaluation/object_detection/01760a841333/runs/v4-reviewed-01/ocr_handoff/` for Cody. The full source dataset and checkpoint remain local artifacts outside Git. A portable ZIP is also available locally at `.runtime/ocr_handoff/v4-reviewed-01-validation.zip`.

The source export metadata identifies Roboflow Front EDS v4 with a CC BY 4.0 notice; individual image source and permission records still need review.
