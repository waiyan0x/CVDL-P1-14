"""Preserve detector training and benchmark evidence outside ignored .runtime."""

import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


MODEL_NAMES = ("yolo11n", "yolo11s", "detr-resnet-50")


def archive_dir(repo_root, dataset_fingerprint, model_name):
    if model_name not in MODEL_NAMES:
        raise ValueError(f"Unknown detector: {model_name}")
    base = Path(repo_root) / "evaluation" / "object_detection" / dataset_fingerprint[:12] / model_name
    for phase in ("train", "validation", "test", "checkpoints"):
        folder = base / phase
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)
    return base


def initialize_archive(repo_root, dataset_fingerprint, model_name):
    base = archive_dir(repo_root, dataset_fingerprint, model_name)
    status_path = base / "status.json"
    if not status_path.is_file():
        _atomic_json(status_path, {
            "model": model_name,
            "dataset_manifest_sha256": dataset_fingerprint,
            "training_status": "pending",
            "validation_status": "pending",
            "test_status": "pending",
        })
    return base


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _copy_if_changed(source, destination):
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        a, b = source.stat(), destination.stat()
        if a.st_size == b.st_size and a.st_mtime_ns == b.st_mtime_ns:
            return True
    shutil.copy2(source, destination)
    return True


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_yolo_run(repo_root, dataset_fingerprint, model_name, run_dir):
    """Copy current YOLO evidence, including partial runs, without changing it."""
    base, run_dir = archive_dir(repo_root, dataset_fingerprint, model_name), Path(run_dir)
    for filename in ("results.csv", "args.yaml", "results.png"):
        _copy_if_changed(run_dir / filename, base / "train" / filename)
    checkpoint_hashes = {}
    for filename in ("best.pt", "last.pt"):
        source = run_dir / "weights" / filename
        if _copy_if_changed(source, base / "checkpoints" / filename):
            checkpoint_hashes[filename] = _sha256(base / "checkpoints" / filename)
    history = base / "train" / "results.csv"
    epochs = 0
    if history.is_file():
        with history.open(newline="", encoding="utf-8") as stream:
            epochs = sum(1 for _ in csv.DictReader(stream))
    record = {
        "model": model_name,
        "dataset_manifest_sha256": dataset_fingerprint,
        "training_status": "complete" if (run_dir / "complete.txt").is_file() else "partial",
        "epochs_recorded": epochs,
        "source_run": str(run_dir),
        "checkpoint_sha256": checkpoint_hashes,
        "validation_status": "saved" if (base / "validation" / "benchmark.json").is_file() else "pending",
        "test_status": "saved" if (base / "test" / "benchmark.json").is_file() else "pending",
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(base / "status.json", record)
    return base


def archive_detr_epoch(repo_root, dataset_fingerprint, history, checkpoint_dir=None):
    """Save DETR losses each epoch and mirror the latest best model if supplied."""
    base = archive_dir(repo_root, dataset_fingerprint, "detr-resnet-50")
    _atomic_json(base / "train" / "history.json", history)
    if checkpoint_dir is not None:
        checkpoint_dir = Path(checkpoint_dir)
        for source in checkpoint_dir.iterdir():
            if source.is_file() and source.name != "complete.txt":
                _copy_if_changed(source, base / "checkpoints" / source.name)
    _atomic_json(base / "status.json", {
        "model": "detr-resnet-50",
        "dataset_manifest_sha256": dataset_fingerprint,
        "training_status": "complete" if checkpoint_dir and (Path(checkpoint_dir) / "complete.txt").is_file() else "partial",
        "epochs_recorded": len(history),
        "validation_status": "saved" if (base / "validation" / "benchmark.json").is_file() else "pending",
        "test_status": "saved" if (base / "test" / "benchmark.json").is_file() else "pending",
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    return base


def archive_benchmark(repo_root, dataset_fingerprint, model_name, phase, report):
    """Save a per-model benchmark report in the tracked results tree."""
    if phase not in ("validation", "test"):
        raise ValueError(f"Unexpected phase: {phase}")
    base = archive_dir(repo_root, dataset_fingerprint, model_name)
    model_report = dict(report)
    model_report["benchmark"] = {model_name: report["benchmark"][model_name]}
    model_report["validation_threshold_sweep"] = [
        row for row in report["validation_threshold_sweep"] if row["model"] == model_name
    ]
    _atomic_json(base / phase / "benchmark.json", model_report)
    status_path = base / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {"model": model_name}
    status[f"{phase}_status"] = "saved"
    status["dataset_manifest_sha256"] = dataset_fingerprint
    status["archived_at_utc"] = datetime.now(timezone.utc).isoformat()
    _atomic_json(status_path, status)
    return base / phase / "benchmark.json"
