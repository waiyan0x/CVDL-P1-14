# Bus EDS Reader

A local FastAPI application that detects Singapore bus display fields, reads
service numbers and destinations, and compares the recognised text with a route
reference table. The frontend uses native HTML, CSS and JavaScript modules.

## Start

On the configured Mac, double-click `start.command` or run:

```sh
bash scripts/run.sh
```

Open **http://127.0.0.1:8000/detect**. The server loads the detector once and uses
local OCR caches. Stop it with Ctrl+C in the launch terminal.

For a fresh Python environment:

```sh
bash scripts/setup.sh
```

Tesseract is optional and must be installed separately with English language
data. The supplied TrOCR weight in Git is an LFS pointer; retrieve the real
checkpoint using authenticated GitHub CLI access:

```sh
.venv/bin/python scripts/fetch_trocr.py
```

Hydrated weights stay in ignored `.cache/trocr/`. Model downloads happen during
setup, not inference. Individual unavailable OCR engines are reported separately.

## Pages

| Page | Purpose |
| --- | --- |
| `/detect` | Upload an image, select a sample, or capture a single camera frame; inspect boxes, crops, OCR and matching. |
| `/live` | Continuous camera input or server-decoded uploaded video with configurable sampling and start/stop/restart/reset. |
| `/evaluation` | Run all three OCR pipelines on one shared set of detections; inspect measured timing and published evaluation evidence. |
| `/models` | Check model provenance, confidence definitions and pipeline methods. |
| `/docs` | FastAPI's generated API documentation. |

The interface follows the supplied Detect design with native Apple system fonts
and grayscale controls. Photographs and cropped regions retain their original
colours. Results come from inference; design-mockup predictions are not used.

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
accuracy. Matching requires an exact recognised service and adequate endpoint
similarity; it does not infer travel direction or verify every road name.
Processing FPS is reciprocal inference time, not sustained camera/display FPS.

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
