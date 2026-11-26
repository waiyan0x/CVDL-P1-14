"""Run this notebook cell first in a fresh Google Colab GPU runtime."""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    from google.colab import drive
except ImportError:
    print("Local kernel: Colab setup skipped; use the existing local paths.")
else:
    drive.mount("/content/drive")
    drive_folder = Path("/content/drive/MyDrive/CVDL-P1-14-colab")
    code_zip = drive_folder / "CVDL-P1-14-v9-colab-code.zip"
    data_zip = drive_folder / "2026-11-25-roboflow-v9-stem-isolated.zip"
    for archive in (code_zip, data_zip):
        if not archive.is_file():
            raise FileNotFoundError(f"Upload this ZIP to Google Drive first: {archive}")

    def extract_checked(archive, destination):
        destination.mkdir(parents=True, exist_ok=True)
        base = destination.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                target = (base / member.filename).resolve()
                if not target.is_relative_to(base):
                    raise ValueError(f"Unsafe ZIP entry: {member.filename}")
            bundle.extractall(base)

    repo_root = Path("/content/CVDL-P1-14")
    extract_checked(code_zip, Path("/content"))
    if not (repo_root / "src").is_dir():
        raise RuntimeError("The code ZIP did not create /content/CVDL-P1-14/src")

    dataset_root = repo_root / "data/training/2026-11-25-roboflow-v9-stem-isolated"
    if not (dataset_root / "preparation_manifest.json").is_file():
        local_zip = Path("/content/2026-11-25-roboflow-v9-stem-isolated.zip")
        shutil.copy2(data_zip, local_zip)
        try:
            extract_checked(local_zip, repo_root / "data/training")
        finally:
            local_zip.unlink(missing_ok=True)
    if not (dataset_root / "preparation_manifest.json").is_file():
        raise RuntimeError(f"The dataset ZIP did not create {dataset_root}")

    results_root = drive_folder / "results"
    output_root = results_root / ".runtime/object_detection_benchmark"
    archive_root = results_root / "Obj-Dect-OCR/object_detection"
    for folder in (output_root, archive_root):
        folder.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "EDS_REPO_ROOT": str(repo_root),
        "EDS_DATASET_ROOT": str(dataset_root),
        "EDS_OUTPUT_ROOT": str(output_root),
        "EDS_ARCHIVE_ROOT": str(archive_root),
        "EDS_YOLO_VIEW_ROOT": str(repo_root / ".runtime/object_detection_benchmark"),
        "EDS_PRETRAINED_ROOT": str(repo_root / ".runtime/object_detection_benchmark/pretrained"),
        "YOLO_CONFIG_DIR": str(repo_root / ".runtime/object_detection_benchmark/ultralytics"),
        "USE_TF": "0",
    })
    os.chdir(repo_root)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.3.158",
        "transformers>=4.52,<5", "timm", "torchmetrics", "pycocotools",
        "pyyaml", "pillow", "nbformat", "ipykernel",
    ], check=True)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError(
            "Select Kernel > Colab > New Colab Server and choose a GPU machine."
        )
    print({"repo": str(repo_root), "dataset": str(dataset_root),
           "outputs": str(output_root), "archive": str(archive_root),
           "gpu": torch.cuda.get_device_name(0)})
