"""Smoke-test the v4 checkpoint through the application's detection/crop path."""

import hashlib
import json
import os
import sys
from pathlib import Path

import cv2
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings
from backend.app.schemas.analysis import FrameOptions
from backend.app.services.detection import Detector
from backend.app.services.pipeline import Pipeline


RUN = ROOT / "evaluation/object_detection/01760a841333/runs/v4-reviewed-01"
DATASET = ROOT / "data/training/2026-11-05-roboflow-v4-reviewed/valid"
OUTPUT = RUN / "validation_review/integration_verification.json"
SAMPLES = {
    "clear_display": "14488614-bus_8_jpg.rf.f42edf43192002dc5ef10238a21c7e38.jpg",
    "multiple_buses": "4ec3e58a-bus_17_jpg.rf.0cda1156155e556073d323b501e069b5.jpg",
    "negative": "IMAGE_2026-10-23_21_56_09_jpg.rf.b74dd5352c689be9c7dcc6a048280656.jpg",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".runtime/ultralytics"))
    config = json.loads((RUN / "detector_config.json").read_text(encoding="utf-8"))
    checkpoint = ROOT / config["checkpoint_local_path"]
    if not checkpoint.is_file() or sha256(checkpoint) != config["checkpoint_sha256"]:
        raise RuntimeError("V4 checkpoint is absent or has the wrong hash")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    settings = Settings(root=ROOT, detector_weights=checkpoint, detector_device=device,
                        detector_image_size=config["input_size"], detector_nms_iou=config["nms_iou"])
    detector = Detector(settings)
    pipeline = Pipeline(settings, detector, None, None)
    evidence = {}
    for name, filename in SAMPLES.items():
        path = DATASET / filename
        image = cv2.imread(str(path))
        if image is None:
            raise FileNotFoundError(path)
        options = FrameOptions(backend="easyocr", detection=config["confidence"],
                               session_id=f"v4-{name}", frame_id=1, source="image")
        prepared = pipeline.prepare(image, options)
        labels = {}
        for item in prepared["detections"]:
            labels[item["label"]] = labels.get(item["label"], 0) + 1
        crop_shapes = {key: list(crop.shape[:2]) for key, (crop, _) in prepared["crops"].items()}
        if any(min(shape) <= 0 for shape in crop_shapes.values()):
            raise RuntimeError("An application crop is empty")
        if name == "negative" and labels:
            raise RuntimeError("Known validation negative produced a detection")
        evidence[name] = {"image": filename, "image_sha256": sha256(path),
                          "detections_by_api_label": labels, "display_groups": len(prepared["groups"]),
                          "crop_count": len(crop_shapes), "crop_shapes_hw": crop_shapes}
        print(f"{name}: {labels}; {len(crop_shapes)} nonempty crops")
    result = {"checkpoint_sha256": config["checkpoint_sha256"], "device": device,
              "confidence": config["confidence"], "nms_iou": config["nms_iou"],
              "app_default_changed": False,
              "scope": "Local application detector, association and crop-path smoke test on three validation stills; no OCR, video or physical-camera claim.",
              "samples": evidence}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
