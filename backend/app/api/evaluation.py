"""Read-only model descriptions and evidence-backed evaluation reports."""
from fastapi import APIRouter, Request

from ..evaluation.catalog import model_catalog
from ..evaluation.provenance import dataset_audit, historical_checkpoint, reference_audit
from ..evaluation.reports import load_reports

router = APIRouter(prefix="/api")


@router.get("/models")
def models(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    pipeline = getattr(runtime, "pipeline", None) or getattr(request.app.state, "pipeline", None)
    return model_catalog(request.app.state.settings, pipeline)


@router.get("/evaluation")
def evaluation(request: Request):
    settings = request.app.state.settings
    reports, report_warnings = load_reports(settings.root)
    ocr_reports = [report for report in reports if report["report_type"] == "reviewed_manifest_benchmark"]
    detection_reports = [report for report in reports if report["report_type"] == "detection_benchmark"]
    return {
        "status": "evaluated" if reports else "unmeasured",
        "accuracy": ocr_reports[0]["engines"] if ocr_reports else None,
        "accuracy_note": "OCR accuracy requires reviewed display transcriptions and a reproducible manifest. A same-frame comparison alone is not an accuracy evaluation.",
        "historical_checkpoint": historical_checkpoint(settings.detector_path),
        "dataset": dataset_audit(settings.root),
        "reference_data": reference_audit(settings.root),
        "reports": ocr_reports, "detection_reports": detection_reports, "report_warnings": report_warnings,
        "limitations": [
            "The bundled split has exact image leakage; removing exact duplicates does not rule out related scenes or near-duplicates.",
            "No reviewed OCR transcriptions are bundled. Sample filenames and CSV endpoint names are not ground truth.",
            "Detection confidence, OCR confidence, and reference similarity measure different things and are not calibrated accuracy.",
            "Live comparison timings depend on hardware, warmup, crop count and image size; reciprocal request time is not sustained video FPS.",
            "Estimated whole-screen envelopes are not model detections and must not count as direct EDS-screen predictions.",
        ],
        "benchmark": {"command": ".venv/bin/python scripts/evaluate.py --manifest PATH_TO_REVIEWED_MANIFEST.json",
                      "manifest_format": "backend/app/evaluation/MANIFEST_FORMAT.md",
                      "report_directory": "evaluation/reports"},
    }
