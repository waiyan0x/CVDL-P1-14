"""Package the local detector code and starting weights for a Colab runtime."""

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "data/training/CVDL-P1-14-v9-colab-code.zip"
DATASET_ZIP = ROOT / "data/training/2026-11-25-roboflow-v9-stem-isolated.zip"
FILES = (
    "README.md",
    "requirements.txt",
    "data/training/README.md",
    "notebooks/object_detection_benchmark.ipynb",
    "notebooks/colab_v9_setup_cell.py",
    "notebooks/README.md",
    "notebooks/build_object_detection_benchmark.py",
    "Obj-Dect-OCR/reports/detection.json",
    ".runtime/object_detection_benchmark/pretrained/yolo11n.pt",
    ".runtime/object_detection_benchmark/pretrained/yolo11s.pt",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    if not DATASET_ZIP.is_file():
        raise FileNotFoundError(DATASET_ZIP)
    paths = {ROOT / name for name in FILES}
    for folder in ("src", "scripts", "docs"):
        paths.update(
            path for path in (ROOT / folder).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in (".py", ".md", ".yaml", ".yml", ".json", ".txt")
        )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Colab package inputs: {missing}")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(DESTINATION, "w", ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(paths):
            bundle.write(path, "CVDL-P1-14/" + path.relative_to(ROOT).as_posix())
    with ZipFile(DESTINATION) as bundle:
        if bad := bundle.testzip():
            raise ValueError(f"Corrupt ZIP member: {bad}")
    print({"code_zip": str(DESTINATION), "bytes": DESTINATION.stat().st_size,
           "sha256": sha256(DESTINATION), "files": len(paths)})
    print({"dataset_zip": str(DATASET_ZIP), "bytes": DATASET_ZIP.stat().st_size,
           "sha256": sha256(DATASET_ZIP)})


if __name__ == "__main__":
    main()
