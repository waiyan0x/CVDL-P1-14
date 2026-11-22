"""Verify selected YOLO11s through app association and uploaded-video decoding."""

from __future__ import annotations

import hashlib
import io
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
from backend.app.media.videos import VideoStore
from backend.app.schemas.analysis import FrameOptions
from backend.app.services.detection import Detector
from backend.app.services.pipeline import Pipeline


DATASET = ROOT / "data/training/2026-10-30-torchvision"
OUTPUT = ROOT / "evaluation/object_detection/bf938f526d2c/runs/baseline-01/deployment/integration_verification.json"
MULTI_DISPLAY = DATASET / "valid/4ec3e58a-bus_17_jpg.rf.0cda1156155e556073d323b501e069b5.jpg"
SINGLE_DISPLAY = DATASET / "valid/IMAGE_2026-10-23_22_04_04_jpg.rf.0cb9ed676b55ae03ba0719f27edc5177.jpg"
NEGATIVE = DATASET / "valid/IMAGE_2026-10-23_21_56_09_jpg.rf.b74dd5352c689be9c7dcc6a048280656.jpg"


class NoTextOCR:
    """Exercise crop dispatch without claiming OCR evidence."""

    def read(self, crop, field, backend):
        return "", 0.0, "not_run_no_local_ocr_assets"


class NoReferenceMatcher:
    def match(self, service, destination, threshold):
        return {"status": "unmatched", "service": None, "endpoint": None,
                "similarity": None, "reason": "Reference CSV unavailable; matching not run.", "routes": []}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, round(.95 * (len(ordered) - 1)))
    return {"runs": len(values), "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[p95_index], 3), "values_ms": [round(value, 3) for value in values]}


def result_summary(result: dict) -> dict:
    labels = {label: sum(item["label"] == label for item in result["detections"])
              for label in ("eds", "bus_number", "route", "destination")}
    return {"status": result["status"], "detections": len(result["detections"]),
            "labels": labels, "displays": len(result["results"]),
            "display_fields": [sorted(item["fields"]) for item in result["results"]],
            "timings": result["timings"]}


def main() -> None:
    for path in (MULTI_DISPLAY, SINGLE_DISPLAY, NEGATIVE):
        if not path.is_file():
            raise FileNotFoundError(path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    settings = Settings(root=ROOT, detector_device=device)
    detector = Detector(settings)
    pipeline = Pipeline(settings, detector, NoTextOCR(), NoReferenceMatcher())

    evidence = {}
    for name, path in (("multiple_displays", MULTI_DISPLAY), ("single_display", SINGLE_DISPLAY), ("negative", NEGATIVE)):
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f"Cannot decode {path}")
        runs = []
        last = None
        for index in range(5):
            last = pipeline.analyse(image, FrameOptions(backend="easyocr", detection=.20,
                session_id=f"integration-{name}", frame_id=index, source="image"))
            runs.append(last["timings"]["detection_ms"])
        evidence[name] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": sha256(path), **result_summary(last),
                          "warmed_detection_latency": summary(runs)}

    camera_image = cv2.imread(str(MULTI_DISPLAY))
    camera_result = pipeline.analyse(camera_image, FrameOptions(backend="easyocr", detection=.20,
        session_id="simulated-camera", frame_id=1, source="camera", source_timestamp_ms=0))

    fixture = ROOT / ".runtime/object_detection_integration_fixture.avi"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    width, height = 800, 534
    writer = cv2.VideoWriter(str(fixture), cv2.VideoWriter_fourcc(*"MJPG"), 2, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Cannot create local AVI fixture.")
    try:
        for path in (MULTI_DISPLAY, SINGLE_DISPLAY, NEGATIVE, MULTI_DISPLAY):
            frame = cv2.imread(str(path))
            writer.write(cv2.resize(frame, (width, height)))
    finally:
        writer.release()

    video_store = VideoStore(settings)
    try:
        media = video_store.add(io.BytesIO(fixture.read_bytes()), "integration_fixture.avi")
        video_runs = []
        video_results = []
        for frame_id, timestamp in enumerate((0, 500, 1000, 1500), 1):
            started = time.perf_counter()
            frame, actual_ms = video_store.frame(media["video_id"], timestamp)
            result = pipeline.analyse(frame, FrameOptions(backend="easyocr", detection=.20,
                session_id="uploaded-video", frame_id=frame_id, source="video", source_timestamp_ms=actual_ms), started)
            video_runs.append(result["timings"]["total_ms"])
            video_results.append({"requested_ms": timestamp, "decoded_ms": actual_ms, **result_summary(result)})
    finally:
        video_store.close()
        fixture.unlink(missing_ok=True)

    report = {
        "schema_version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checkpoint": str(settings.detector_path.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_sha256": sha256(settings.detector_path),
        "device": device,
        "settings": {"image_size": settings.detector_image_size, "confidence": .20,
                     "nms_iou": settings.detector_nms_iou},
        "image_evidence": evidence,
        "simulated_camera": {**result_summary(camera_result),
            "limitation": "Uses a labelled still image through the camera response path; no physical camera or moving-bus claim."},
        "uploaded_video": {"metadata": media, "frames": video_results, "total_latency": summary(video_runs),
            "limitation": "Local MJPG fixture built from labelled stills verifies upload/decode/frame identity and detector flow, not field-video generalisation."},
        "ocr": {"status": "not_verified", "reason": "No local EasyOCR/TrOCR assets or Tesseract executable were available. A no-text adapter exercised crop dispatch only; OCR accuracy and latency are not reported."},
        "reference_matching": {"status": "not_verified", "reason": "data/bus_information.csv was unavailable."},
        "physical_camera": {"status": "not_verified", "reason": "Requires user-approved browser permission and real camera hardware/field scenes."},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
