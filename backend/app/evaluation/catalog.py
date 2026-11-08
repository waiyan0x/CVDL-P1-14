"""Runtime model descriptions, confidence semantics, and pipeline method."""
import importlib.metadata
import os
import platform
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from .provenance import file_hash


def _version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


@lru_cache(maxsize=4)
def _tesseract_version(executable: str | None) -> str | None:
    if not executable:
        return None
    try:
        return subprocess.run([executable, "--version"], capture_output=True, text=True,
                              timeout=5, check=True).stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def _artifacts(path: Path, root: Path) -> dict:
    files = [path] if path.is_file() else sorted(p for p in path.glob("*") if p.is_file())
    return {_display_path(file, root): file_hash(file) for file in files}


def model_catalog(settings, pipeline=None) -> dict:
    root = settings.root
    detector = settings.detector_path
    detector_hash = file_hash(detector) if detector.is_file() else None
    v4_hash = "97150601de39a999754015648cad2ef930842d52e8e37eb77d7576ffe2da33b5"
    baseline_hash = "01d832cb6eda71dcf4a88e6ebbafc080f9dc299be8161c76ab15c75f7c60c2e3"
    if detector_hash == v4_hash or (detector_hash is None and "01760a841333" in str(detector)):
        detector_id, expected_hash, operating_confidence = "eds-yolo11s-v4-reviewed-01", v4_hash, .50
        detector_note = "Validation-selected YOLO11s from the reviewed-v4 experiment; human annotation review remains open."
    elif detector_hash == baseline_hash:
        detector_id, expected_hash, operating_confidence = "eds-yolo11s-baseline-01", baseline_hash, .20
        detector_note = "Historical baseline-01 YOLO11s checkpoint."
    else:
        detector_id, expected_hash, operating_confidence = "eds-yolo11s-custom", None, None
        detector_note = "Custom or unverified detector checkpoint; compare its hash with the saved experiment records."
    available = pipeline.ocr.backends() if pipeline is not None else []
    errors = pipeline.ocr.availability() if pipeline is not None and hasattr(pipeline.ocr, "availability") else {}
    common = "An engine-specific heuristic, not calibrated accuracy; confidence scores cannot rank different engines."
    engines = [
        {"id": "easyocr", "name": "YOLO + EasyOCR", "path": _display_path(settings.easyocr_dir, root),
         "version": _version("easyocr"), "description": "English OCR baseline on detected text-field crops; CPU inference.",
         "confidence_definition": "Character-count-weighted mean of EasyOCR text confidence. " + common,
         "limitations": ["Small LED characters, glare and blur can reduce recognition quality."]},
        {"id": "tesseract", "name": "YOLO + Tesseract", "path": shutil.which("tesseract"),
         "version": _tesseract_version(shutil.which("tesseract")),
         "description": "Installed English Tesseract baseline; single-line service and block destination recognition.",
         "confidence_definition": "Character-count-weighted mean of nonnegative Tesseract word confidence, scaled to 0–1. " + common,
         "limitations": ["LED dot patterns and mixed line layouts may produce empty or incorrect text."]},
        {"id": "trocr", "name": "YOLO + fine-tuned TrOCR", "path": _display_path(settings.trocr_dir, root),
         "source_path": "models/trocr-finetuned", "version": _version("transformers"),
         "description": "Supplied VisionEncoderDecoder checkpoint, loaded lazily from hydrated local Git LFS weights; no runtime downloads.",
         "confidence_definition": "Geometric mean of generated token probabilities. " + common,
         "limitations": ["TrOCR is a text-line recogniser; multiline destination crops can lose text.",
                         "First use includes model-loading time; warmed timing must be reported separately."]},
    ]
    for engine in engines:
        engine["available"] = engine["id"] in available
        engine["unavailable_reason"] = errors.get(engine["id"]) if not engine["available"] else None
        if not engine["available"] and not engine["unavailable_reason"]:
            engine["unavailable_reason"] = "Engine is not loaded or its required local weights/executable are unavailable."
        engine["artifact_files"] = _artifacts(Path(engine["path"]), root) if engine["id"] == "tesseract" and engine["path"] else (
            _artifacts(root / engine["path"], root) if engine["path"] else {})
    return {
        "detector": {"id": detector_id, "name": "Selected fine-tuned YOLO11s", "path": _display_path(detector, root),
                     "available": detector.is_file(), "version": _version("ultralytics"),
                     "sha256": detector_hash,
                     "artifact_files": _artifacts(detector, root),
                     "filename_note": detector_note,
                     "classes": [
                         {"id": 0, "label": "front_eds", "api_label": "eds", "used": True},
                         {"id": 1, "label": "front_eds_num", "api_label": "bus_number", "used": True},
                         {"id": 2, "label": "front_eds_route", "api_label": "route", "used": True},
                         {"id": 3, "label": "front_eds_destination", "api_label": "destination", "used": True},
                     ],
                     "training_class_filter": [0, 1, 2, 3], "device": settings.detector_device,
                     "image_size": settings.detector_image_size,
                     "confidence_definition": "YOLO confidence that a box contains its predicted class; not OCR correctness or model accuracy.",
                     "operating_confidence": operating_confidence, "nms_iou": settings.detector_nms_iou,
                     "checkpoint_sha256_expected": expected_hash,
                     "note": "Panel, number, route and destination are all requested. Model labels are translated explicitly to the stable API labels."},
        "ocr_engines": engines,
        "pipeline": [
            {"id": "input", "title": "Validate and sample", "description": "Validate image/video content, decode a frame, retain frame identity and media time, and bound image dimensions."},
            {"id": "detection", "title": "Detect display fields", "description": "Run the supplied YOLO checkpoint once. Comparisons share identical boxes and crops across all three OCR engines."},
            {"id": "association", "title": "Associate and crop", "description": "Assign text fields to known EDS screens before pairing remaining nearby fields. Preserve separate display IDs within each frame."},
            {"id": "ocr", "title": "Read visible text", "description": "Read service and destination crops with the selected local engine; retain raw text and engine-specific confidence."},
            {"id": "matching", "title": "Compare references", "description": "Look up an exact recognised service and compare sufficiently confident observed text with that service's CSV endpoints."},
            {"id": "display", "title": "Publish one frame result", "description": "Return boxes, crops, raw text, references, separate scores and stage timings with the processed frame identity. No tracking or temporal text merging is claimed."},
        ],
        "preprocessing": {"detector": f"Images are bounded before inference and letterboxed by YOLO to size {settings.detector_image_size}.",
                          "ocr": "Small service-number crops may be enlarged; destination fields preserve their line layout. Each engine applies its own documented image preparation."},
        "matching": {"service": "Exact recognised service lookup; no nearest-number guessing.",
                     "destination": "Normalised text/line similarity against that service's origin and destination; weak matches are rejected.",
                     "score_definition": "Reference string similarity, not an OCR or detection confidence and not calibrated accuracy.",
                     "limitations": "The CSV lacks verified road-name and direction coverage. A route endpoint match does not establish travel direction."},
        "estimated_screen": {"source": "field_union", "confidence": None,
                             "description": "When no enclosing EDS screen is predicted, paired service/destination fields form a padded estimated envelope.",
                             "display": "Dashed outline labelled estimated; no fabricated detection confidence.",
                             "limitation": "It approximates display extent and is excluded from direct screen-detection metrics."},
        "runtime_hardware": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
                             "processor": platform.processor(), "logical_cpus": os.cpu_count(), "detector_device": settings.detector_device,
                             "torch_threads": settings.torch_threads},
    }
