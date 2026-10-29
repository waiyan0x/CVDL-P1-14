# EDS Reader development contract

The supplied Detect HTML reference defines the visual design. Use four pages:
`/detect` (also `/`), `/live`, `/evaluation`, `/models`. Native HTML, CSS and ES
modules; Apple system font; grayscale UI with original photos/crops in colour.
Keep the reference's top navigation, 1200px content width, generous heading,
image/result columns, segmented controls and compact result panels. No fake
predictions, fabricated confidence or unverified accuracy figures.

## Modules

`backend/app/`: app factory/lifespan, configuration, API routes, schemas,
inference services, individual OCR adapters, image/video media handling,
evaluation provenance. `frontend/`: page templates, shared styles and small
JavaScript modules for API, media controls, renderers and page controllers.
`tests/`: backend and browser contract/lifecycle tests. Keep datasets/weights in
their existing paths. Remove `demo/` after migration; update launch/setup/docs.
Avoid oversized modules; aim for focused files under 250 lines, splitting by
responsibility rather than arbitrary line counts.

## API contract (snake_case JSON)

- `GET /api/health`: `{ready,error,backends,default_backend,limits}`. `backends`
  is a list of available IDs: `easyocr`, `tesseract`, `trocr`. Limits include
  image/video upload bytes, maximum video duration and default/minimum sampling
  interval. Missing engines do not disable otherwise usable engines.
- `GET /api/samples`: `[{id,name,url,source}]`; image URL returns original image.
- `POST /api/analysis`: multipart `file` or `sample_id`, plus `backend`,
  `detection` (default .3), `ocr_threshold` (.25), `similarity` (.7),
  `session_id`, `frame_id` (nonnegative monotonic integer), `source`
  (`image|sample|camera|video`), `source_timestamp_ms` (nonnegative media time),
  `captured_at` (ISO timestamp). Metadata is echoed in `frame`.
- `POST /api/videos`: bounded multipart `file`; validates actual decodability,
  returns `{video_id,name,width,height,duration_ms,fps,url}`. `url` is optional
  playback only; inference uses server decoding even if browser playback fails.
- `POST /api/videos/{video_id}/frames`: JSON same options and metadata, plus
  `timestamp_ms`. Decode that position and return the same analysis shape with
  actual decoded media time. No job queue.
- `DELETE /api/videos/{video_id}`: release upload; missing uploads are harmless.
- `POST /api/comparisons`: same multipart input as analysis, no backend needed.
  Detect once and use identical boxes/crops for the three OCR pipelines. Return
  `{frame,image,width,height,detections,comparisons:[{backend,status,result,error}]}`.
  Successful `result` uses analysis shape below; unavailable/failed engines have
  null result and a clear error. Engine scores must not be ranked as accuracy.
- `GET /api/evaluation`: provenance/limitations, historical checkpoint metrics,
  dataset audit, optional verified report(s). Accuracy is null until a reviewed
  transcription manifest is provided. Explicit dataset and run identity.
- `GET /api/models`: detector and OCR engine descriptions, paths, availability,
  confidence definitions, class labels, preprocessing and pipeline method.

Analysis response:

```json
{
  "frame": {"session_id":"...","frame_id":1,"source":"camera",
    "source_timestamp_ms":0,"captured_at":"...","processed_at":"..."},
  "status":"matched",
  "message":"Reference endpoint matched",
  "backend":"easyocr",
  "image":"data:image/jpeg;base64,...", "width":1280, "height":720,
  "detections":[{"id":"field-1","display_id":"display-1",
    "label":"bus_number","box":[1,2,3,4],"confidence":0.9,"source":"model"}],
  "results":[{"display_id":"display-1","status":"matched","message":"...",
    "screen":{"box":[0,0,100,30],"source":"field_union","confidence":null,
      "crop":"data:image/jpeg;base64,..."},
    "fields":{"bus_number":{"id":"field-1","box":[1,2,3,4],
      "confidence":0.9,"raw":"3","ocr_confidence":0.8,
      "crop":"data:image/jpeg;base64,..."}},
    "match":{"status":"matched","service":"3","endpoint":"Tampines Bus Interchange",
      "similarity":0.9,"reason":"...","routes":[]}}],
  "timings":{"detection_ms":1,"preprocessing_ms":1,"ocr_ms":1,
    "matching_ms":1,"total_ms":4},
  "processing_fps":250
}
```

States: `no_eds`, `unreadable`, `partial`, `unknown_match`, `matched`.
HTTP errors always `{error:{code,message}}`; validation errors are human-readable.
Use 400 invalid input, 404 missing media/sample, 413 too large, 422 invalid
options, 429 busy, 503 not ready and 500 processing failure. Never return raw
stack traces. Standard FastAPI OpenAPI remains available at `/docs`.

## Frame and input lifecycle

Client sends at most one inference request at a time, captures the latest frame
only after the configured interval, and skips missed intervals. Inference lock
rejects excess work before decoding. Session/generation identity prevents stale
responses repainting after stop/reset/source changes. Frame IDs are local to a
session; display IDs are local to a frame (no tracking claim).

New input/mode and reset clear results/overlays and invalidate pending responses.
While processing retain the preceding result with its frame/time label. Stop or
end retains the last completed processed frame explicitly labelled as stopped.
Errors stop processing and clear current result; retry/restart remains available.
Camera tracks, object URLs and backend uploads are cleaned on switching/reset
and page exit. Uploaded video restart begins at zero; camera restart reacquires
camera. Sample interval is user-configurable, never an asserted achieved FPS.

Assign fields to detected screens before pairing leftovers by constrained
geometry. Never pair across known screen owners. Screen-only detections remain
visible as unreadable. Estimated EDS boxes have dashed outlines and no detection
confidence; field IDs/numbers link boxes to their single result panel.

## Evaluation

Compare YOLO + EasyOCR, YOLO + Tesseract and YOLO + supplied fine-tuned TrOCR.
Same-frame comparison measures behaviour/timing, not accuracy without ground
truth. Verified reports require reviewed transcriptions, split/hash provenance,
hardware/settings, exact accuracy/CER and latency protocol. Report known split
overlap. Historical checkpoint scores are separate from independently verified
metrics; saved training class filter is [1,2], so these are not whole-EDS scores.

## Verification

Backend tests cover bounded/invalid inputs, metadata, busy admission, ownership,
screen-only detections, model failure isolation, video decode/time and cleanup.
Browser checks cover all four pages at 320/768/1024/1440px, real image inference,
comparison, video sampling, simulated camera, permission denial, stop/reset,
input switches and stale-response rejection. Console must remain clean.
