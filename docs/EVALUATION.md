# Evaluation evidence

The application is designed to compare the validation-selected YOLO11s detector
with EasyOCR, Tesseract and the supplied fine-tuned TrOCR. A same-image comparison
runs the detector once and shares the resulting boxes/crops. At the current
handoff, only real EasyOCR integration observations have been recorded locally;
Tesseract and fine-tuned TrOCR remain pending. Reported text, engine-specific
confidence and processing time form a functional comparison, not an accuracy
measurement without reviewed transcriptions.

## Latest four-class detector experiment

The corrected Roboflow v4 dataset was used for `v4-reviewed-01`: all three
models have training and validation records, and validation-selected YOLO11s has
a final held-out test. Its validation mAP50:95 is `0.3510`; test mAP50:95 is
`0.3270` at confidence `0.50` and NMS IoU `0.70`. The complete table, per-class
AP, run settings and evidence paths are in
[`RESULTS.md`](../evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md).
This checkpoint is now installed as the application default; the earlier
baseline is preserved as historical evidence. The human v4 annotation review
and real moving-bus evaluation remain open.

## Earlier application detector measurement

The earlier application detector benchmark is recorded under
`evaluation/object_detection/bf938f526d2c/runs/baseline-01/`. YOLO11s was selected
using validation mAP50:95 (`0.4274`) with 640-pixel input, confidence `0.20` and NMS
IoU `0.70`. It detects panel, number, route and destination classes. See
`docs/OBJECT_DETECTION_DEPLOYMENT.md` for installation and the application contract,
and `docs/OBJECT_DETECTION_HANDOFF.md` for the exact stopping point and remaining work.

## Historical field-detector measurement

Reproduce the committed report:

```sh
.venv/bin/python scripts/evaluate_detector.py
```

`evaluation/reports/detection.json` records the exact checkpoint SHA256,
image/annotation hashes, exclusions, library versions, CPU details and settings.
The run uses 13 labelled images from the bundled test split after removing exact
training overlaps, repeated test content and the unlabelled annotated example.
Only service-number and destination classes `[1, 2]` are evaluated. The saved
training metadata also used those classes. These figures do not measure EDS
screen detection or OCR.

One original `.jpg` actually contains AVIF data. Evaluation explicitly converts
it to JPEG in temporary staging and records both hashes, preventing the validator
from silently dropping it. Source images and labels are never edited.

The committed measurement gives approximately 0.961 precision, 1.000 recall,
0.995 mAP50 and 0.749 mAP50–95. This small subset uses existing annotations;
annotation quality, related scenes, near-duplicate images and original training
provenance remain unverified. It does not establish generalisation to unseen
bus videos. Validator speed is mean time per image, not sustained web-app FPS.

Metrics use the [Ultralytics validation API](https://docs.ultralytics.com/modes/val/).
The page distinguishes these measured results from historical checkpoint scores.
Report loading verifies detector/image/annotation hashes against available files.

## OCR ground truth and benchmarks

No reviewed OCR transcriptions are bundled. Bounding-box labels and route CSV
endpoints are not transcriptions, and sample filenames are not used as truth.
OCR accuracy therefore remains unavailable until a reviewed manifest is supplied.

See [MANIFEST_FORMAT.md](../backend/app/evaluation/MANIFEST_FORMAT.md) and its
adjacent empty example. Have a reviewer transcribe the visible fields and screen
coordinates, record image hashes and dataset/review identity, then run:

```sh
.venv/bin/python scripts/evaluate.py --manifest /absolute/path/to/reviewed.json
```

Use a dedicated idle application server. The CLI excludes warmup from timing,
filters known exact training overlap by default, includes missed detections in
accuracy, associates multiple displays by geometry, and measures exact accuracy,
case/whitespace-normalized accuracy, character error rate and median/p95 latency.
Engine confidence values do not determine accuracy rankings. Reports retain
successes/failures, settings, hardware, errors, hashes and limitations.

Reports are loaded from `evaluation/reports/`. The interface shows whether their
evidence still matches the available artifacts; a reviewed manifest is a human
attestation and does not itself prove independent annotation quality.

## Dataset limitations

The content-hash audit currently finds five validation images with exact training
overlap and one test image matching two training copies. Original splits remain
unchanged. Exact-hash filtering cannot identify all related scenes or OCR training
overlap. The 609-row route reference includes duplicates and missing data and
does not establish travel direction or every road name.

Camera and video smoke tests use simulated camera frames and a clearly labelled
still-photo video fixture. They validate controls, decoding and data flow; real
camera hardware, moving buses, glare and network/CPU load require field testing.
