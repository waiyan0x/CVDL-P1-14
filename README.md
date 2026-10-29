# Bus EDS Reader and data preparation

Prepare local bus images for front/side electronic destination sign detection.
Standalone Python scripts own processing; the single notebook only displays
augmentation comparisons and representative scene categories.

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
