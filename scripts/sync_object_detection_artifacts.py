"""Mirror existing local detector runs into the results archive."""

import hashlib
from pathlib import Path

from object_detection_artifacts import MODEL_NAMES, archive_yolo_run


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/training/2026-10-30-torchvision"
manifest = DATASET / "augmentation_manifest.json"
if not manifest.is_file():
    raise FileNotFoundError(manifest)
fingerprint = hashlib.sha256(manifest.read_bytes()).hexdigest()
runs = ROOT / ".runtime/object_detection_benchmark" / fingerprint[:12] / "runs"

if runs.is_dir():
    for experiment in runs.iterdir():
        if not experiment.is_dir() or experiment.name in MODEL_NAMES:
            continue
        for model_name in ("yolo11n", "yolo11s"):
            run_dir = experiment / model_name
            if (run_dir / "results.csv").is_file():
                base = archive_yolo_run(ROOT, fingerprint, model_name, run_dir, experiment.name)
                print(base)
