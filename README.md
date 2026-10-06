# Video-Based Bus EDS Recognition System

A computer vision project to recognise information shown on Singapore bus **Electronic Display Signage (EDS)**. The intended use case is helping visually impaired commuters identify an approaching bus service and its displayed destination or road information.

**Project status:** This repository contains project documentation, a bus reference CSV, annotated image splits, and model artifacts. It does not yet contain the planned web application or reported evaluation results. The proposed interface produces text; accessibility for independent use has not been established.

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

The detection threshold, OCR threshold, output interval, and handling of changing or multiple displays remain to be defined. Sampling at 15 FPS is an initial input setting, not a measured processing rate or latency claim. The proposed message for low OCR confidence is **“No bus information detected.”**

## Application and scope

The planned application runs on **localhost**, with **FastAPI** as the backend and **HTML, CSS, and JavaScript** for the interface. It is intended to accept a computer camera stream and uploaded videos and show raw OCR text, the selected reference-based result, and clearly labelled confidence values for debugging. Detection confidence, OCR confidence, and reference similarity are separate measures.

Audio output, mobile deployment, and cloud deployment are outside the current scope. Recognition for buses in other countries and optional audio output are future directions.

## Data and model plan

The documentation describes Singapore bus images discovered through Google image search and route information sourced from Wikipedia. The included [`data/bus_information.csv`](data/bus_information.csv) has route number, origin, and destination fields, but no dedicated road-name, travel-direction, or verified EDS-text fields. Reference matching therefore cannot be assumed to validate every road name or distinguish every direction. Source permissions, attribution, data quality, and software or model licences need review before redistribution.

The documentation proposes fine-tuning pretrained detection and OCR models and lists YOLO11n, YOLO11s, EasyOCR, and TrOCR as candidates. The repository also contains a YOLO checkpoint and a TrOCR checkpoint, but their evaluation and status as final pipeline components are not documented. Fuzzy matching against the reference CSV is the initial correction approach. A closest match is not necessarily a correct match, so acceptance and rejection rules still need to be specified.

## Planned evaluation

The documentation recommends measuring:

| Stage | Proposed measures |
| --- | --- |
| EDS detection | mAP@0.5:0.95 and recall |
| OCR | Character Error Rate and field-level exact-match accuracy |
| Complete pipeline | Accuracy of complete results, processing FPS, and median/p95 latency |

Planned comparisons include detection configurations, baseline versus fine-tuned OCR, raw versus reference-corrected text, and performance under image transformations and unseen video. Test images and related video frames should be separated from training data before augmentation. **No numerical results or performance targets have been reported.**

## Current repository contents

| File | Purpose |
| --- | --- |
| [Bus_EDS_Project_Complete_Overview.docx](Bus_EDS_Project_Complete_Overview.docx) | Concise project scope, workflow, evaluation outline, and open questions |
| [Bus_EDS_Project_Documentation.docx](Bus_EDS_Project_Documentation.docx) | Detailed decisions, data and model considerations, proposed evaluation, and references |
| [`data/`](data/) | Bus reference CSV and annotated train, validation, and test image splits |
| [`models/`](models/) | YOLO and TrOCR model artifacts |

The workflow image referenced by the documents is not in this repository. There are currently no installation or run instructions because the application has not been added.

## Next steps

1. Confirm EDS formats, visible-field requirements, annotation rules, and reference-data coverage.
2. Prepare and verify detection labels, OCR transcriptions, and held-out evaluation data.
3. Establish baselines, fine-tune candidate models, and compare recognition quality.
4. Implement reference matching, rejection behaviour, and the local camera/video interface.
5. Measure end-to-end accuracy, robustness, throughput, and latency on declared hardware.

See the two documents above for the full list of open decisions and supporting source notes.
