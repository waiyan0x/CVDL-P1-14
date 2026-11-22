"""Run real EasyOCR on YOLO11s component crops without claiming OCR accuracy."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
import time

import cv2
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings
from backend.app.schemas.analysis import FrameOptions
from backend.app.services.detection import Detector
from backend.app.services.ocr.registry import OCRRegistry
from backend.app.services.pipeline import Pipeline


DATASET = ROOT / "data/training/2026-10-30-torchvision/valid"
CASES = {
    "multiple_displays": DATASET / "4ec3e58a-bus_17_jpg.rf.0cda1156155e556073d323b501e069b5.jpg",
    "single_display": DATASET / "IMAGE_2026-10-23_22_04_04_jpg.rf.0cb9ed676b55ae03ba0719f27edc5177.jpg",
}
OUTPUT = ROOT / "evaluation/object_detection/bf938f526d2c/runs/baseline-01/deployment/easyocr_integration_verification.json"


class NoReferenceMatcher:
    def match(self, service, destination, threshold):
        return {"status": "unmatched", "service": None, "endpoint": None,
                "similarity": None, "reason": "Reference CSV unavailable; matching not run.", "routes": []}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    settings = Settings(root=ROOT, detector_device=device)
    detector = Detector(settings)
    registry = OCRRegistry(settings)
    if "easyocr" not in registry.backends():
        raise RuntimeError(f"EasyOCR unavailable: {registry.availability()['easyocr']}")
    pipeline = Pipeline(settings, detector, registry, NoReferenceMatcher())
    results = {}
    all_ocr = []
    all_total = []
    for case_name, path in CASES.items():
        image = cv2.imread(str(path))
        if image is None:
            raise FileNotFoundError(path)
        case_runs = []
        last = None
        for run in range(3):
            last = pipeline.analyse(image, FrameOptions(backend="easyocr", detection=.20,
                session_id=f"easyocr-{case_name}", frame_id=run, source="image"))
            case_runs.append(last["timings"])
            all_ocr.append(last["timings"]["ocr_ms"])
            all_total.append(last["timings"]["total_ms"])
        displays = []
        for display in last["results"]:
            fields = {}
            for label, field in display["fields"].items():
                fields[label] = {"raw": field["raw"], "ocr_confidence": field["ocr_confidence"],
                                 "ocr_confidence_method": field["ocr_confidence_method"],
                                 "detection_confidence": field["confidence"]}
            displays.append({"display_id": display["display_id"], "status": display["status"], "fields": fields})
        results[case_name] = {"image": str(path.relative_to(ROOT)).replace("\\", "/"),
            "detections": len(last["detections"]), "displays": displays, "runs": case_runs}

    report = {
        "schema_version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device": device,
        "backend": "easyocr",
        "available_backends": registry.backends(),
        "unavailable_backends": {key: value for key, value in registry.availability().items() if value},
        "settings": {"detector_confidence": .20, "detector_nms_iou": settings.detector_nms_iou,
                     "ocr_threshold": .25, "runs_per_image": 3},
        "cases": results,
        "latency": {"ocr_median_ms": round(statistics.median(all_ocr), 3),
                    "ocr_p95_ms": round(percentile(all_ocr, .95), 3),
                    "total_median_ms": round(statistics.median(all_total), 3),
                    "total_p95_ms": round(percentile(all_total, .95), 3)},
        "accuracy": None,
        "limitations": [
            "No reviewed OCR transcriptions are available, so raw readings and confidence are observations, not accuracy evidence.",
            "EasyOCR runs on CPU in the application adapter; YOLO11s runs on the recorded detector device.",
            "Reference matching was not run because data/bus_information.csv is unavailable.",
            "Tesseract and the supplied fine-tuned TrOCR assets remain unavailable locally.",
            "The two images are diagnostic integration cases, not an OCR benchmark dataset."
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
