# Video-Based Bus EDS Recognition System

A computer vision project to recognise information shown on Singapore bus **Electronic Display Signage (EDS)**. The intended use case is helping visually impaired commuters identify an approaching bus service and its displayed destination or road information.

**Project status (8 October 2026):** A working local FastAPI demo connects the supplied YOLO11n detector, EasyOCR, optional Tesseract, and the supplied TrOCR checkpoint to image upload, browser camera/video input, reference matching, and a text interface. Independent evaluation and accessibility for independent use remain pending.

## Run the demo

On the configured Mac, double-click `start-demo.command` or run `bash scripts/run-demo.sh`, then open **http://127.0.0.1:8000**. Choose **Project photo 01** and **Recognise image** for the first example. The demo runs locally with cached model weights.

For a fresh setup, run `bash scripts/setup.sh`. TrOCR weights can be retrieved separately with `.venv/bin/python scripts/fetch_trocr.py`, using authenticated GitHub CLI access to this private repository. The original Git LFS pointer is retained; hydrated weights live in the ignored `.cache/trocr/` directory.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the presentation sequence, recovery steps, limitations, and verification commands.

The demo detects service/destination field regions without a bus-front detection gate. Matching requires an exact recognised service and compares observed text/lines with that service's endpoints. Raw road text is retained. Detection/OCR/matching thresholds are adjustable; weak matches are rejected. Video processing allows one request at a time and skips frames while inference is busy.

## Project goals

- Detect EDS screens directly in camera or uploaded video, without a separate bus detection stage.
- Recognise visible service numbers, destinations, and road names from the detected screens using optical character recognition (OCR).
- Compare recognised text with bus reference information to help correct OCR errors.
- Present continuing results through a local web application with low latency.
- Evaluate recognition quality and processing speed on representative Singapore bus displays.

The intended coverage includes different operators and EDS formats. Actual coverage will depend on the data collected and the results of testing.

## Proposed workflow

**Offline preparation:** Collect bus images and route information; annotate EDS boundaries; create verified text transcriptions; prepare reference data; then train and compare detection and OCR models.

**Runtime pipeline:**

```text
Computer camera or uploaded video
    → sample frames (initial plan: up to 15 FPS)
    → detect EDS regions directly
    → crop accepted regions
    → recognise displayed text with OCR
    → compare text with bus reference data
    → display raw OCR and reference-based results at a controlled interval
```

The demo has adjustable detection/OCR/matching thresholds and processes video frames sequentially with a minimum 200 ms gap after each result. The original 15 FPS input plan is not a measured processing rate or latency claim. Low-confidence service text produces **“No bus information detected.”** Multiple nearby fields are paired spatially; changing display content is processed per frame without temporal merging.

## Application and scope

The demo runs on **localhost**, with **FastAPI** as the backend and **HTML, CSS, and JavaScript** for the interface. It accepts images and browser-playable videos, supports a browser camera stream, and shows raw OCR, reference results, cropped fields, and labelled confidence values. Detection confidence, OCR confidence, and reference similarity are separate measures. The documents retain the original design discussion; the demo guide describes implemented behavior.

Audio output, mobile deployment, and cloud deployment are outside the current scope. Recognition for buses in other countries and optional audio output are future directions.

## Data and model plan

The documentation describes Singapore bus images discovered through Google image search and route information sourced from Wikipedia. The included [`data/bus_information.csv`](data/bus_information.csv) has route number, origin, and destination fields, but no dedicated road-name, travel-direction, or verified EDS-text fields. Reference matching therefore cannot be assumed to validate every road name or distinguish every direction. Source permissions, attribution, data quality, and software or model licences need review before redistribution.

The documentation proposes fine-tuning and comparing YOLO11n, YOLO11s, EasyOCR, and TrOCR. The demo uses the supplied YOLO11n checkpoint and supports the supplied fine-tuned TrOCR checkpoint alongside OCR baselines. These choices are provisional until evaluated independently. Reference matching requires an exact recognised service and sufficient endpoint similarity; no destination is invented when recognition is weak. Similarity and OCR scores are heuristics rather than calibrated accuracy.

## Planned evaluation

The documentation recommends measuring:

| Stage | Proposed measures |
| --- | --- |
| EDS detection | mAP@0.5:0.95 and recall |
| OCR | Character Error Rate and field-level exact-match accuracy |
| Complete pipeline | Accuracy of complete results, processing FPS, and median/p95 latency |

Planned comparisons include detection configurations, baseline versus fine-tuned OCR, raw versus reference-corrected text, and robustness on unseen video. Test images and related frames should be separated from training before augmentation. **No independent accuracy results or validated performance targets have been reported.** The demo measures each request's processing time; its reciprocal processing capacity is not sustained video FPS. Historical metrics inside the supplied detector checkpoint do not establish independent performance on these data.

## Current repository contents

| File | Purpose |
| --- | --- |
| [Bus_EDS_Project_Complete_Overview.docx](Bus_EDS_Project_Complete_Overview.docx) | Concise project scope, workflow, evaluation outline, and open questions |
| [Bus_EDS_Project_Documentation.docx](Bus_EDS_Project_Documentation.docx) | Detailed decisions, data and model considerations, proposed evaluation, and references |
| [`data/`](data/) | Bus reference CSV and annotated train, validation, and test image splits |
| [`models/`](models/) | YOLO and TrOCR model artifacts |
| [`demo/`](demo/) | Local FastAPI backend, recognition pipeline, and browser interface |
| [`scripts/`](scripts/) | Setup, launch, model retrieval, and browser smoke verification |
| [`tests/`](tests/) | Matching, field pairing, and API validation tests |
| [DEMO_GUIDE.md](DEMO_GUIDE.md) | Presentation sequence and known limitations |

The workflow image referenced by the documents is not in this repository. The included data have exact duplicates across training/validation/test, so bundled examples must not be treated as independent evaluation. The demo does not change the original dataset splits.

## Next steps

1. Confirm EDS formats, visible-field requirements, annotation rules, and reference-data coverage.
2. Prepare and verify detection labels, OCR transcriptions, and held-out evaluation data.
3. Establish baselines, fine-tune candidate models, and compare recognition quality.
4. Validate and improve the implemented matching, rejection behavior, spatial field pairing, and local camera/video interface.
5. Measure end-to-end accuracy, robustness, throughput, and latency on declared hardware.

See the two documents above for the full list of open decisions and supporting source notes.
