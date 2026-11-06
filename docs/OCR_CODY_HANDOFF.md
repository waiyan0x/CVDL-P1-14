# OCR handoff for Cody and his Codex

Start on `bren-object-detection`. Read this page, then the linked crop and evaluation contracts before changing OCR code. The current detector is the reviewed-v4 YOLO11s model; keep its confidence at `0.50`, NMS IoU at `0.70`, and image size at `640` for the first OCR comparison. Preserve `baseline-01` as historical detector evidence.

## What to find in the repo

| Location | Use |
| --- | --- |
| [`ocr_handoff/`](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/ocr_handoff/README.md) | Committed v4 **validation-only** crops, `manifest.json`, and blank `transcriptions_template.csv`. Start here without downloading the full dataset. |
| [`OCR_HANDOFF.md`](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/OCR_HANDOFF.md) | Crop counts, export settings, provenance, and split limitations. |
| [`OBJECT_DETECTION_DEPLOYMENT.md`](OBJECT_DETECTION_DEPLOYMENT.md) | Four-class mapping, selected detector hash, installation and inference contract. |
| [`backend/app/services/ocr/`](../backend/app/services/ocr/) | Existing EasyOCR, Tesseract and TrOCR adapters plus shared resize logic in `registry.py`. |
| [`pipeline.py`](../backend/app/services/pipeline.py) | Detector-to-crop-to-OCR flow and field ownership. Keep OCR text separate from reference matching. |
| [`MANIFEST_FORMAT.md`](../backend/app/evaluation/MANIFEST_FORMAT.md) and [`manifest.example.json`](../backend/app/evaluation/manifest.example.json) | Required **image-level** reviewed manifest for the application benchmark. This is a different format from the crop transcription CSV. |
| [`evaluate.py`](../scripts/evaluate.py) and [`EVALUATION.md`](EVALUATION.md) | Three-engine application comparison, output metrics, overlap handling and limitations. |
| [`DEVELOPMENT_CONTRACT.md`](DEVELOPMENT_CONTRACT.md) | API, comparison and result behavior expected by the app. |

The crop package has 221 annotation crops and 160 detector-predicted crops from 53 validation images. The 157 annotation text crops are listed in `transcriptions_template.csv`; all transcription cells are blank and review status is `pending`. `ground_truth/` means **box coordinates from annotations**, not verified text. `predicted/` is what OCR receives after detection. `front_eds` is panel context; `front_eds_num`, `front_eds_route`, and `front_eds_destination` are the text fields. The ten zero-box validation images have no predicted boxes at the saved detector threshold.

## Current state

- The application exposes `/detect`, `/models`, and `/evaluation`; its comparison path detects each image once and shares crops across the three OCR engines.
- EasyOCR has a historical **baseline detector** integration check with raw readings and timing at [`easyocr_integration_verification.json`](../evaluation/object_detection/bf938f526d2c/runs/baseline-01/deployment/easyocr_integration_verification.json). It is not a v4 OCR benchmark or an accuracy score. [`verify_easyocr_integration.py`](../scripts/verify_easyocr_integration.py) hardcodes the old dataset, output path and `0.20` threshold; update it or create a new v4 script before using it for v4 evidence.
- Tesseract requires a system executable with English language data. The supplied fine-tuned TrOCR requires hydrated local weights; a Git LFS pointer alone will not run it. Check engine availability in `/models` and record failures explicitly.
- No reviewed OCR transcription manifest or measured v4 OCR accuracy is committed. Detector mAP is not text accuracy. The reference CSV and filenames are not text ground truth.
- Full v4 source images, trained detector weights and OCR model caches are Git-ignored. A Git pull supplies these committed validation crops, but not the full dataset or checkpoint. Ask Brendan for the checkpoint/source export if live inference, new crop exports or train-split fine-tuning are needed.

## Recommended work sequence

1. **Confirm inputs and scope.** Pull the branch; inspect the crop README, `manifest.json`, class mapping and `git status`. Work from the 53-image validation package. Do not tune on the detector's held-out test set.
2. **Create reviewed truth.** Have a human read each visible number, route and destination exactly as shown, including line breaks. Fill a copy of `transcriptions_template.csv`, keeping source crop, reviewer, date, legibility and exclusion reasons. Mark unreadable/unknown text distinctly from a reviewed empty string. Check that annotation crops really contain the intended field. For the application benchmark, separately prepare the reviewed **image-level** JSON specified by `MANIFEST_FORMAT.md`, including display boxes, image SHA-256 values, negative images and review attestation. Do not convert unreviewed CSV rows into asserted truth.
3. **Run the three OCR baselines.** Make EasyOCR, Tesseract and TrOCR available; capture version/model identity and device. Run all three on the **same predicted validation crops**, with identical preprocessing and detector settings. Save raw output, per-field exact and normalized accuracy, character error rate, empty/error counts and median/p95 time. Also test annotation crops as a separate diagnostic to quantify the detector crop effect. Report number, route and destination separately, plus an overall count-weighted result.
4. **Improve preprocessing and handling.** Try a small, logged set of padding, resize, contrast and line-order variants on validation only; keep paired inputs identical across engines. Inspect errors by small text, bus angle, lighting, glare, LED color, clipping and multi-line destination. Define how empty, partial and low-confidence reads are shown. OCR confidence methods differ by engine and are not calibrated accuracy probabilities.
5. **Fine-tune only with train-split truth.** If a baseline justifies it, obtain or export **training** crops and verified train transcriptions. Keep validation for model/setting selection and a separate, untouched test split for the final evaluation. Save a new model/version, training settings and checkpoint provenance; compare it to the untouched baselines on the same reviewed validation cases.
6. **Freeze settings, then test once.** Select the OCR engine and preprocessing using validation results. Run an independent held-out OCR test only after that choice is fixed, with reviewed truth and no train/validation leakage. Distinguish raw OCR correctness from route-reference matching and end-to-end detector-plus-OCR correctness. Publish hashes, exclusions, model versions, latency, field metrics and representative failure cases with the report.

## Commands on the Windows workspace

Run from the repository root in PowerShell. These commands check assets and launch the existing application; the benchmark requires the reviewed image-level JSON from step 2.

```powershell
git status --short --branch
venv\detector\Scripts\python.exe scripts\install_selected_detector.py --verify-only
venv\detector\Scripts\python.exe scripts\install_easyocr_assets.py
venv\detector\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell terminal after the app is ready:

```powershell
venv\detector\Scripts\python.exe scripts\evaluate.py --manifest C:\path\to\reviewed-v4-ocr-validation.json --detection 0.50
```

The benchmark saves JSON in `evaluation/reports/` by default. It uses the application's shared detection path, includes misses in end-to-end text scoring, and reports unavailable engines separately. The crop CSV is for direct crop-level OCR experiments; it is **not** accepted by `scripts/evaluate.py`. On a fresh machine, create the app environment with `requirements-app.txt` or the repo setup instructions first. Use [`install_selected_detector.py`](../scripts/install_selected_detector.py) with `--source PATH` when a verified v4 checkpoint is transferred. Install Tesseract separately and retrieve TrOCR weights using [`fetch_trocr.py`](../scripts/fetch_trocr.py) with the required authenticated access.

## Files Cody should leave for the next handoff

- Reviewed transcription source with reviewer/date, field/crop IDs, exclusions and source hashes; an image-level benchmark manifest when using the app evaluator.
- Reproducible baseline and preprocessing commands or scripts, pinned settings, environment versions and model hashes.
- A results table for all three OCR engines, broken down by field and image condition, with raw-text metrics, errors and latency. Label crop-only and end-to-end results separately.
- Chosen OCR configuration and a short explanation of the validation decision. Save any later held-out test as a separate immutable run.

Keep the reviewed validation crop package and the existing detector reports intact. Any new evaluation output should use a new run name rather than overwrite historical evidence.
