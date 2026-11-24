# Bus EDS Reader and data preparation

Prepare local bus images for front/side electronic destination sign detection.
Standalone Python scripts own data preparation. The data visual-check notebook
displays augmentation comparisons and representative scene categories; the
separate detector benchmark notebook records model evaluation.

Model dataset: **`data/training/2026-10-24/`**.
Its current local export contains **420 training, 39 validation and 20 test
images (479 total)**, verified against the COCO records on 2026-10-29.
The training COCO groups outputs under 140 source names (three outputs each);
the exact original/augmentation breakdown is not recorded in a manifest.
`data/labelled/` is the annotation source before augmentation. The current
training files identify a Roboflow export and lack the manifest required by the
configured loader. See the training README before loading or rebuilding it.
See the [training dataset](data/training/README.md) and
[readiness handoff](docs/data_preparation/TRAINING_READINESS.md).

The completed detector benchmark instead used the separate manifest-backed
`data/training/2026-10-30-torchvision/` export with 411 train, 39 validation
and 20 test images. Do not substitute the older Roboflow folder for that run.

## Commands for a new batch

Run from the repository root (the folder containing `scripts/`, `src/` and
`requirements.txt`). The example below processes a separate `2026-10-31` batch;
replace that date consistently for another batch. The configured defaults still
point to `2026-10-24`, so keep the new batch arguments explicit.

```powershell
python -m pip install -r requirements.txt

# 1. Put the new raw images in data/raw/2026-10-31/, then freeze their splits.
python scripts/01_prepare_and_split.py --cutoff 2026-10-31 --output "data/raw/2026-10-31/splits" --write

# 2. Annotate all images and open the local review editor after inference.
python scripts/02_auto_annotate.py --cutoff 2026-10-31 --input "data/raw/2026-10-31/splits" --output "experiments/eds_autodistill/outputs/2026-10-31-run-001" --limit 0 --run --review
```

In the editor, correct the boxes/classes and save **Accept positive** or
**Confirm negative** for every image. Progress is saved in the experiment's
`review_decisions.json`. Viewing overlay PNGs alone does not record acceptance;
there is no need to send overlay paths to anyone. Automatic checks flag label
issues; visual confirmation of front/side EDS coverage and negatives is manual.

After every image is accepted, click **Export reviewed dataset** with destination
`data/labelled/2026-10-31`, or stop the editor with Ctrl+C and use the export
command below. Use one export method; an existing destination is not overwritten.

```powershell
# 3. Export saved decisions (skip if already exported through the editor).
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --export "data/labelled/2026-10-31"

# 4. Audit the accepted dataset. Resolve failures before continuing.
python scripts/00_audit_dataset.py --input "data/labelled/2026-10-31" --report ".runtime/labelled-audit-2026-10-31.json"

# 5. Run only after the audit reports automated_checks_passed: true.
python scripts/03_augment_dataset.py --cutoff 2026-10-31 --input "data/labelled/2026-10-31" --output "data/training/2026-10-31" --multiplier 3 --write
```

The final dataset is `data/training/2026-10-31/{train,valid,test}/`, with images and
`_annotations.coco.json` in each split. Training contains originals plus variants;
validation/test images and COCO JSON are copied unchanged. Separate batch paths
preserve the existing `2026-10-24` dataset; batches are not automatically merged.

To resume review without rerunning inference:

```powershell
python scripts/review_annotations.py --run-dir "experiments/eds_autodistill/outputs/2026-10-31-run-001" --serve
```

The experiment's `overlays/{train,val,test}/` folders contain `__draft.png` images
with explicit boxes/classes and `__raw.png` detector proposals. The editor shows
your current corrections; static overlays retain the initial predictions.

See [script arguments and defaults](scripts/README.md) for path overrides,
planning commands, and working with existing accepted labels. Without `--write`,
split/augmentation commands only plan/validate; annotation needs `--run` for
inference and defaults to three images per split unless `--limit 0` is supplied.
No model training is included.

| Location | Purpose |
| --- | --- |
| [scripts/](scripts/README.md) | Independent phase commands and flags |
| [docs/data_preparation/](docs/data_preparation/README.md) | Phase sequence, contracts and augmentation rationale |
| [src/data_preparation/](src/data_preparation/README.md) | Reusable loading, splitting, annotation, augmentation and preprocessing code |
| [notebooks/](notebooks/README.md) | Read-only before/after plots and three images per coverage category |
| [data/](data/README.md) | Local dataset layout, tracked manifests and coverage |
| [docs/annotation/](docs/annotation/README.md) | Autodistill annotation, isolated drafts and review |
| [Annotation guide](docs/annotation/guide.md) | Front/side EDS scope, four bbox classes, exclusions and review rules |

Inspect/group raw images -> freeze train/validation/test -> annotate and review ->
validate accepted COCO -> augment training only. Keep validation/test unchanged.
The existing snapshot is already split; do not replace its membership.

Full raw/labelled/training exports, model caches and virtual environments stay
local. Curated presentation samples in `data/samples/` are tracked. Notebook
outputs are cleared before committing so images are not embedded in Git.

```powershell
python -m unittest discover -s tests -v
```

## Dependency environments

`requirements.txt` retains the pinned data-preparation environment.
`requirements-app.txt` retains the reader application's dependency constraints;
`scripts/setup.sh` and `requirements-dev.txt` use that application list.
The workflows require different Transformers major versions. Install them in
separate virtual environments rather than combining both dependency files.
The Mac app launcher uses `.venv`; use another environment for preparation there.

## Reader application

A local FastAPI application that detects Singapore bus display fields, reads
service numbers and destinations, and compares the recognised text with a route
reference table. The frontend uses native HTML, CSS and JavaScript modules.

## Start

On the configured Mac, double-click `start.command` or run:

```sh
bash scripts/run.sh
```

Open **http://127.0.0.1:8000/**. The server loads the detector once and uses
local OCR caches. Stop it with Ctrl+C in the launch terminal.

For a fresh Python environment:

```sh
bash scripts/setup.sh
```

The selected OCR model, fine-tuned PaddleOCR, is in `models/paddleocr-finetuned/`
(hash-checked against its `provenance.json` at start-up). PaddlePaddle does not
support the app's Python version, so it runs in a separate Python 3.12
environment that the app starts as a worker process. It defaults to
`.cache/paddle-baseline-env/bin/python`; set `EDS_PADDLE_PYTHON` (and optionally
`EDS_PADDLE_MODEL`) to use another one. Create it with:

```sh
python3.12 -m venv .cache/paddle-baseline-env
.cache/paddle-baseline-env/bin/pip install paddlepaddle==3.2.2 paddleocr==3.3.2
```

With the `paddleocr` engine, if a display has no usable number or destination
crop (none detected, or no text read), the public pretrained PaddleOCR in
`models/paddleocr-pretrained/` reads the whole display instead. The first
service-shaped token becomes the number and the rest the destination. These
fields are marked `ocr_source: whole_display_fallback` in the response. On whole
displays the pretrained model matched 11 of 41 displays and the fine-tuned model 5,
both far below field crops; see
`evaluation/ocr_scoring/whole-display-fallback-20261121/`. The fallback worker
starts on first use. Worker messages go to `.runtime/logs/paddle_worker.log`. If the environment or
weights are missing, PaddleOCR is reported as unavailable and the other engines
still work. The supplied TrOCR weight in Git is an LFS pointer; retrieve the real
checkpoint using authenticated GitHub CLI access:

```sh
.venv/bin/python scripts/fetch_trocr.py
```

Hydrated weights stay in ignored `.cache/trocr/`. Model downloads happen during
setup, not inference. Individual unavailable OCR engines are reported separately.

## Pages

| Page | Purpose |
| --- | --- |
| `/` | Project home page with an illustrated bus arrival and a link to Live. |
| `/detect` | Upload an image, select a sample, or capture a single camera frame; inspect boxes, crops, OCR and matching. |
| `/live` | Continuous camera input or server-decoded uploaded video with configurable sampling and start/stop/restart/reset. |
| `/evaluation` | Run all three OCR pipelines on one shared set of detections; inspect measured timing and published evaluation evidence. |
| `/models` | Check model provenance, confidence definitions and pipeline methods. |
| `/docs` | FastAPI's generated API documentation. |

The reader pages use a monochrome layout. The home page illustrates Singapore’s
green public buses at a stop. Photographs and cropped regions retain their
original colours, and displayed recognition results come from inference.

## Spoken bus announcements

On Detect or Live, choose **Read result aloud** to hear the latest bus service
and any matched reference destination. On Live, enable **Automatic announcements**
to hear new readings after two consistent frames. The app uses the browser's
speech synthesis and prefers an installed English voice.

For a distance estimate, start a Live camera session. With the camera fixed and
one bus facing it, open **Calibrate distance** and set the measured distance to
the sign. The app compares the current sign width with the reference width and
rounds the result to five metres. Use the same bus, camera position and zoom.
The estimate requires a fresh frame with a single, fully visible model-detected
sign and the same recognised service. Stopping the camera clears calibration.
This estimate is for demonstration. Use station guidance when boarding.

## Structure

```text
backend/app/
  main.py             Application factory, lifespan and page routing
  config.py           Validated environment configuration
  api/                Thin HTTP route handlers
  schemas/            Frame, result, confidence and timing contracts
  services/           Detector, ownership, pipeline, matching and OCR adapters
  media/              Bounded image/video decoding and upload lifecycle
  evaluation/         Provenance, dataset audit and benchmark reports
frontend/
  pages/              Detect, Live, Evaluation, Models & Method
  assets/             Shared styles and focused JavaScript modules
scripts/              Setup, launch, model retrieval and evaluation commands
tests/                Backend, frontend lifecycle and browser verification
data/                 Original labels/images/reference table; separate UI samples
models/               Supplied YOLO and TrOCR artifacts
```

See [docs/DEVELOPMENT_CONTRACT.md](docs/DEVELOPMENT_CONTRACT.md) for component
boundaries, HTTP payloads and input/result lifecycle. The former `demo/` package
is replaced by this application; its completed version remains on Git's `demo`
branch.

## Object detection handoff

The latest four-class YOLO11n, YOLO11s and DETR comparison is
[`v4-reviewed-01`](evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md)
on the corrected Roboflow v4 export. YOLO11s was selected by validation
mAP50:95 (`0.3510`) and scored `0.3270` on the final held-out test. The earlier
[`baseline-01`](evaluation/object_detection/bf938f526d2c/runs/baseline-01/RESULTS.md)
remains as historical evidence. The app now defaults to v4 YOLO11s at confidence
`0.50` and NMS `0.70`; install its ignored local checkpoint using the
[deployment instructions](docs/OBJECT_DETECTION_DEPLOYMENT.md). Continue from
the [handoff](docs/OBJECT_DETECTION_HANDOFF.md).
For Cody's OCR work, start with the [OCR handoff README](docs/OCR_CODY_HANDOFF.md).
The latest run also has a [validation NMS and crop review](evaluation/object_detection/01760a841333/runs/v4-reviewed-01/validation_review/REVIEW.md)
and a saved v4 detector configuration; the Jy/Brendan annotation review is on hold.

Jy and Brendan still need to review the class rules, negatives and capture
groups. The v4 dataset and checkpoints are local ignored files; a Git pull
provides reports but not those payloads. A changed dataset requires a new
version and run ID. OCR accuracy and
real moving-bus camera performance have not been established.

## Processing behaviour

Each frame carries a session ID, frame number, source timestamp and capture time.
Boxes use the exact returned preview coordinates. Fields are assigned to actual
EDS detections before remaining fields are paired spatially. Numbered field boxes
link to individual result panels. Display IDs apply within one frame, not across
frames; this is not a bus tracking system.

A padded **estimated EDS** envelope is drawn only around paired fields when no
model screen encloses them. It has a dashed outline and no detection confidence.
The supplied checkpoint is YOLO11n despite the `best_v6.pt` filename. Its saved
training filter targets service-number/destination classes; historical checkpoint
scores do not establish whole-screen detection accuracy.

Only one inference request runs at a time. Live sampling captures the newest
camera frame or requests the current video timestamp after the chosen interval;
it skips missed intervals rather than building a queue. Late responses from an
old input/session are discarded. Stop retains the last completed frame; reset or
switching inputs clears results. Errors are explicit and do not preserve a
misleading current match. Uploaded videos are temporary and bounded by size,
duration, count and expiry.

Detection confidence, OCR confidence and reference similarity remain separate.
OCR scores use different definitions across engines and are not calibrated
accuracy. Matching requires an exact recognised service (a number missing from
the reference gives "unable to detect") and a destination that reaches the
similarity cutoff (default 65 of 100, the `similarity` option .65) while leading
the next distinct reference endpoint by 10 points; otherwise the value is
withheld and the raw OCR is kept. Both text sides pass through
`data/reference/abbreviations.csv` before scoring. If a destination fits another
service better than the number read, the number is kept and the result is
flagged as a conflict. Matching does not infer travel direction or verify road
names. Rules, settings and results: `docs/REFERENCE_MATCHING.md`.
Processing FPS is reciprocal inference time, not sustained camera/display FPS.

## Reference matching

Matching code: `backend/app/services/reference_matching.py` (used by
`matching.py`). Reference: `data/reference/bus_information.cleaned.csv`, a cleaned
copy of `data/bus_information.csv` (`data/reference/README.md`). Try it from a
terminal without the web app:

```sh
python scripts/match_reference.py --number 14E --destination "> TAMP1NES INT"
python scripts/match_reference.py --crop-dir runs/matching/bus_374
python scripts/match_reference.py --photo data/samples/distance-and-image-quality/close-readable-eds.jpg --save-dir runs/matching
python scripts/evaluate_reference_matching.py
```

Model weights for the terminal tool live in `models/local/` (gitignored): `paddleocr/` (fine-tuned
PaddleOCR, reads number, destination and route crops), `paddleocr-pretrained/` (reads whole-display
crops), `yolo/best.pt` (fine-tuned YOLO11s). Check which
PaddleOCR weights are installed in `docs/REFERENCE_MATCHING.md` (hash table). Cutoff and line-swap benchmark on 40
labelled photos: `evaluation/photo_benchmark/PHOTO_BENCHMARK.md` (`scripts/benchmark_photo_threshold.py`,
`scripts/benchmark_crop_confidence.py`). Photo mode also reads the whole display line by line when the field
crops leave gaps (`backend/app/services/panel_lines.py`). Each result also carries a one-line `announcement`, e.g.
`Bus 174 to Kampong Bahru Bus Terminal, via Corporation Rd.` (rules in `docs/REFERENCE_MATCHING.md`).

Settings in use: `ratio` scoring, cutoff 65, margin 10, line swap on, conflict policy
`keep_number`, route crop fallback `check`. Full usage, decision rules and
validation/test results: `docs/REFERENCE_MATCHING.md` and
`evaluation/reference_matching/REFERENCE_MATCHING_RESULTS.md`.

## Configuration

Configuration uses `EDS_` environment variables; see `.env.example`. The launcher
uses `BUS_EDS_PORT` for the local HTTP port. `.env` files are not loaded
automatically: export values in the terminal before running the application.
Keep a single server worker so model memory and temporary video ownership are
shared predictably. GPU/MPS compatibility depends on the installed framework;
the detector defaults to CPU and TrOCR uses MPS when available.

## Evaluation and tests

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
npm ci
npm test
npm run test:browser
```

Browser tests use an isolated installed Google Chrome against the running local
server. Camera checks use a simulated camera, and video fixtures are generated
from still images; these checks do not establish performance on real bus video.

For a reproducible OCR benchmark, prepare a reviewed transcription manifest and
run `scripts/evaluate.py --help`. The evaluation page separates current-input
comparisons, historical detector metadata and verified reports. There is no
reviewed OCR ground truth in the bundled data, so no verified OCR accuracy is
claimed. Existing dataset splits contain exact train/validation/test overlap;
the evaluation tooling reports it and never treats filenames or CSV endpoints
as ground truth. See [docs/EVALUATION.md](docs/EVALUATION.md).

The original coursework documents remain project background. Audio output,
cloud deployment and mobile deployment are outside this implementation.
