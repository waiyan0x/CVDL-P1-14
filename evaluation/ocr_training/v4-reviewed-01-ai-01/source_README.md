# OCR handoff: reviewed v4 train crops

`ground_truth/` contains tight crops from COCO annotations. Training export has no detector predictions. Panel crops are context; text OCR should primarily use number, route and destination.

`manifest.json` links each crop to its source image, coordinates, class and source name. For predicted crops it also records prediction confidence and diagnostic same-class IoU, neither of which proves readable or correct text. `transcriptions_template.csv` lists annotation-based text crops with blank transcription and reviewer fields: a human must review crops and enter verified text before CER, word error or exact-text accuracy can be reported.

The crop geometry has no padding or resizing. Keep train, validation and held-out test separate; this package uses train only. Source-name groups are a starting point for overlap review, not proof of scene independence. Do not use the detector's final test for tuning.

Dataset images, crops and checkpoint are local artifacts and not automatically included in Git. The ZIP beside this folder can be transferred directly.
