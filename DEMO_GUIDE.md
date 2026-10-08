# Demo on this Mac

Open **http://127.0.0.1:8000**. The server is left running after setup.

If the server has stopped, double-click `start-demo.command`, or run:

```bash
bash scripts/run-demo.sh
```

Keep that terminal open. Use Chrome for camera/video demonstrations and allow camera access when prompted. The models and reference data run locally; uploads are processed on this Mac.

## A short presentation

1. Start with **Project photo 01** and **Recognise image** using EasyOCR. Point out the number/destination boxes, raw OCR, separate detection/OCR scores, reference endpoint, and timing. This image recognises service **3** and matches **Tampines Bus Interchange** in the supplied CSV.
2. Select **Project photo 02** (service 272), recognise it, and explain that weak destination text can be rejected while a service reference is still available. Recognition is imperfect; the output does not force a destination.
3. Choose **Supplied fine-tuned TrOCR** and recognise photo 01 to show the existing OCR checkpoint. The first request loads the model and takes longer. Its score is a token probability heuristic and is not directly comparable with EasyOCR confidence.
4. Choose EasyOCR again and **Replay photos** to show continuing updates. This is explicitly a photo replay, not real moving-bus footage. Use **Stop** before changing input.
5. Upload a JPEG/PNG or an H.264 MP4/WebM, or use the camera to show an EDS image. The browser sends one frame at a time and skips frames while processing is busy. Video/camera results depend on display size, blur, and glare.

The result panel retains raw road/destination text. Endpoint references come from the supplied CSV and **do not establish travel direction**. No result is read from sample filenames or detection annotation files.

## What is implemented

- Supplied YOLO11n checkpoint detects service-number, destination and EDS regions directly. The bus-front class is not a gate. When the checkpoint supplies no enclosing EDS box, a padded envelope is inferred from paired text fields and drawn as a dashed amber **EDS screen · estimated** box, with no invented confidence score. It approximates the display extent, not the exact physical screen boundary.
- EasyOCR baseline, optional installed Tesseract baseline, and the supplied fine-tuned TrOCR checkpoint.
- Exact service lookup, fuzzy matching of observed text/lines against that service's endpoint references, and configurable rejection thresholds.
- Image uploads, local browser camera capture, browser-playable video input, bundled images, and photo replay.
- Detection overlays, cropped fields, raw OCR, labelled reference output, three separate scores, recent history, and measured server/request timing.

## Limits to state honestly

- This is a functional recognition prototype, not a validated accessibility tool. There is no audio output.
- OCR is sensitive to crop quality and LED layouts. TrOCR uses a text-line recogniser; full multi-line fields may lose text. Neither model guarantees correct results.
- The CSV has 609 rows, duplicate rows, a missing destination for 92B, and no dedicated road-name/direction coverage. The demo preserves raw text instead of forcing road names to endpoints.
- The included dataset has duplicates across training/validation/test. Bundled examples demonstrate functionality, not independent test accuracy. No training-data or split edits were made for this demo.
- The displayed processing capacity is 1000 divided by the current frame's server milliseconds. It is not sustained video FPS, a 15 FPS claim, or capture-to-display latency. Request round-trip timing is shown separately.
- Multiple nearby field boxes are paired spatially; this is not tracking. Alternating displays are processed per frame, without temporal merging.

## Recovery

- **Camera denied:** use photo upload/replay or enable camera access for localhost in Chrome. Browser camera permissions must be granted by the presenter.
- **Unsupported video:** use H.264 MP4 or WebM. Browser playback support determines accepted video codecs.
- **No text / wrong output:** use photo 01 for the reliable first example. Keep raw OCR visible and explain rejection. Do not lower thresholds merely to manufacture a match.
- **Server stopped:** run `start-demo.command`. If port 8000 is already occupied by this demo, use the existing server. For a different port: `BUS_EDS_PORT=8001 bash scripts/run-demo.sh`, then open port 8001.
- **Setup on another machine:** `bash scripts/setup.sh` downloads EasyOCR weights; optional `python scripts/fetch_trocr.py` requires authenticated GitHub CLI access to this private repository. The supplied YOLO checkpoint is already included.

## Verification

Unit/API tests: `.venv/bin/python -m pytest -q` (install pytest/httpx if absent).
Browser smoke script: `node scripts/browser-smoke.cjs` with Playwright available and Chrome installed, while the server runs.
The browser tests use generated fixture video and a simulated camera, not a real bus-stop performance test.
