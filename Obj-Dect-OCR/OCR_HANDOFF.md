# OCR handoff for Cody

Start with the single [reviewed-v4 OCR package](ocr_handoff/v4-reviewed-01/README.md) on `bren-object-detection`. Pull its Git LFS ZIP and extract it. The ZIP contains `train/`, `valid/`, and `test/` annotation crops in four class folders, the original full-photo COCO export, the selected YOLO11s checkpoint, validation detector-predicted crops, and CSV/Excel transcription templates. Do not substitute Jy's v5 export for this run.

## Related project documentation

- [Evaluation](EVALUATION.md): benchmark metrics, reporting, and ground-truth requirements.
- [Development contract](../docs/DEVELOPMENT_CONTRACT.md): application modules, API behavior, and integration conventions.
- [Object detection deployment](../docs/OBJECT_DETECTION_DEPLOYMENT.md): install and verify the selected YOLO11s detector for end-to-end tests.
- [Object detection handoff](../docs/OBJECT_DETECTION_HANDOFF.md): detector results, class rules, and remaining integration work.

## What is in the package

| Path inside the extracted ZIP | Purpose |
| --- | --- |
| `train/`, `valid/`, `test/` | Annotation crops under `front_eds/`, `front_eds_num/`, `front_eds_route/`, and `front_eds_destination/`. Each split has a blank `transcriptions_template.csv`. |
| `transcriptions_template.xlsx` | The same rows in Excel sheets named `train`, `valid`, and `test`. |
| `valid/predicted/` | Actual YOLO11s validation crops for testing OCR on detector output. |
| `manifest.json` | Source image, annotation, crop path, split, and SHA-256 provenance. |
| `valid/detector_predictions_manifest.json` | Validation prediction boxes, confidence, and diagnostic IoU links. |
| `source_coco/` | Original full photos, train/valid/test COCO annotations, and verified preparation manifest. Needed to run the detector on whole test photos. |
| `detector/yolo11s-best.pt` | Selected detector checkpoint. SHA-256: `97150601de39a999754015648cad2ef930842d52e8e37eb77d7576ffe2da33b5`. |

The four folders identify **bounding-box classes**, not the text displayed in them. `front_eds` is panel context; number, route, and destination are text fields. Every transcription cell is blank. Human reviewers must transcribe visible text, record their own names and actual review dates, and mark unreadable or excluded crops rather than guess from filenames or the route CSV. Keep related source images in one split; the `source_name` field is a starting point, not proof of independence.

There are 735/53/53 source images and 2,754/221/171 annotation crops in train/valid/test. The text-field rows are 1,917/157/118. Zero-box negatives have no annotation crop and are listed in `manifest.json`. The 160 validation predicted crops are separate from the annotation crops. Detector settings are confidence `0.50`, NMS IoU `0.70`, and image size `640`. The previous `baseline-01` detector remains historical evidence.

## Cody's starting sequence

1. Pull `bren-object-detection` with Git LFS enabled. Verify and extract the one ZIP in the [package folder](ocr_handoff/v4-reviewed-01/README.md). It contains both full photos and crops; a tiny LFS pointer file is not the package.
2. Review the crop and image provenance. Have humans fill copies of the split transcription templates. Keep test truth closed while selecting models and preprocessing.
3. Install the three OCR engines. The adapters are under [`backend/app/services/ocr/`](../backend/app/services/ocr). EasyOCR assets use [`install_easyocr_assets.py`](../scripts/install_easyocr_assets.py); Tesseract requires its system executable and English data; TrOCR requires hydrated model weights via [`fetch_trocr.py`](../scripts/fetch_trocr.py). Check `/models` for availability.
4. Compare EasyOCR, Tesseract, and TrOCR on the **same validation predicted crops**. Also compare annotation crops separately to isolate detector-crop errors. Record raw text, field-level exact and normalized accuracy, character error rate, unreadable/empty/error counts, and median/p95 latency. Keep OCR confidence separate from detection confidence and reference similarity.
5. Compare padding, resizing, contrast, perspective, and line ordering using validation only. Inspect errors by lighting, angle, distance, glare, blur, LED color, clipping, and multiline destination. If justified by the baseline, fine-tune on verified **training** text only and save model/version/settings.
6. Freeze the selected OCR settings, then evaluate on a reviewed, independent test set once. Report raw OCR before reference matching and end-to-end detector-plus-OCR separately. Do not use the detector's prior held-out result to tune a new configuration.

For an application-level benchmark, prepare the reviewed **image-level** JSON described in [`MANIFEST_FORMAT.md`](../backend/app/evaluation/MANIFEST_FORMAT.md); the crop CSV is not accepted by [`scripts/evaluate.py`](../scripts/evaluate.py). The app comparison path detects each image once and shares crops across OCR engines. See [`EVALUATION.md`](EVALUATION.md) and [`DEVELOPMENT_CONTRACT.md`](../docs/DEVELOPMENT_CONTRACT.md) for metrics and API behavior. The old [`verify_easyocr_integration.py`](../scripts/verify_easyocr_integration.py) is hardcoded to the earlier baseline and does not establish v4 OCR accuracy.

Run from the repo root in PowerShell after installing the application environment:

```powershell
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --source C:\path\to\extracted\detector\yolo11s-best.pt
venv\detector\Scripts\python.exe scripts\install_easyocr_assets.py
venv\detector\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, once the image-level truth is reviewed:

```powershell
venv\detector\Scripts\python.exe scripts\evaluate.py --manifest C:\path\to\reviewed-v4-ocr-validation.json --detection 0.50
```

Reports go to `Obj-Dect-OCR/reports/` by default. Save each new experiment under a new run name; preserve historical detector results and do not overwrite the supplied dataset.
