"""Mirror existing local detector runs into the results archive."""

import hashlib
from pathlib import Path

from object_detection_artifacts import MODEL_NAMES, archive_yolo_run, initialize_archive


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/training/2026-10-30-torchvision"
manifest = DATASET / "augmentation_manifest.json"
if not manifest.is_file():
    raise FileNotFoundError(manifest)
fingerprint = hashlib.sha256(manifest.read_bytes()).hexdigest()
runs = ROOT / ".runtime/object_detection_benchmark" / fingerprint[:12] / "runs"

for model_name in MODEL_NAMES:
    base = initialize_archive(ROOT, fingerprint, model_name)
    if model_name.startswith("yolo") and (runs / model_name / "results.csv").is_file():
        archive_yolo_run(ROOT, fingerprint, model_name, runs / model_name)
    print(base)
