"""Content-based dataset audit and checkpoint-bound historical evidence."""
import csv
import hashlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CHECKPOINT_SHA256 = "5bebdc21a38af9be76287f0a65957172ffda8cfdb55b1e953d0849b1c849523d"


@lru_cache(maxsize=1024)
def _hash_file(path: str, size: int, modified: int) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    stat = path.stat()
    return _hash_file(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def image_hashes(root: Path, split: str) -> dict[str, list[str]]:
    hashes = defaultdict(list)
    for path in sorted((root / "data/images" / split).glob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            hashes[file_hash(path)].append(path.name)
    return dict(hashes)


def dataset_audit(root: Path) -> dict:
    hashes = {split: image_hashes(root, split) for split in ("train", "val", "test")}
    splits, fingerprint = {}, hashlib.sha256()
    for split, groups in hashes.items():
        names = [name for group in groups.values() for name in group]
        labels = root / "data/labels" / split
        splits[split] = {"images": len(names), "labelled_images": sum(
            (labels / (Path(name).stem + ".txt")).exists() for name in names),
            "unique_images": len(groups)}
        for digest, names_for_hash in sorted(groups.items()):
            fingerprint.update(f"{split}:{digest}:{','.join(names_for_hash)}\n".encode())
    overlap = []
    for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
        groups = [{"sha256": digest, first: hashes[first][digest], second: hashes[second][digest]}
                  for digest in sorted(hashes[first].keys() & hashes[second].keys())]
        overlap.append({"splits": [first, second], "image_count": sum(len(g[second]) for g in groups),
                        "unique_hashes": len(groups), "groups": groups})
    warnings = []
    if any(item["image_count"] for item in overlap):
        warnings.append("Exact image duplicates cross dataset splits. Bundled examples are not an independent test set.")
    if any(item["images"] != item["labelled_images"] for item in splits.values()):
        warnings.append("Some images have no detection-label file; they must not silently enter labelled evaluation.")
    return {"id": "bundled-bus-images", "fingerprint_sha256": fingerprint.hexdigest(),
            "splits": splits, "overlap": overlap, "warnings": warnings,
            "ocr_ground_truth_available": False,
            "ground_truth_note": "YOLO text files contain bounding boxes and class IDs, not OCR transcriptions."}


def historical_checkpoint(path: Path) -> dict:
    identity_matches = path.is_file() and file_hash(path) == CHECKPOINT_SHA256
    return {"label": "Historical checkpoint metadata", "source": "Saved train_metrics and train_args in best_v6.pt",
            "checkpoint_sha256": CHECKPOINT_SHA256, "identity_matches": identity_matches,
            "training_date": "2025-06-24T11:25:02.380865", "ultralytics_version": "8.3.158",
            "training_classes": [1, 2], "training_dataset_path": "dataset/data.yaml",
            "metrics": {"precision": .86588, "recall": .94754, "map_50": .94759, "map_50_95": .55886}
            if identity_matches else None,
            "warning": "These are saved training-run metrics with unverified dataset provenance, not independent evaluation or whole-EDS scores. Training used classes [1, 2]."
            if identity_matches else "The detector file differs from the audited checkpoint; historical scores are withheld."}


def reference_audit(root: Path) -> dict:
    path = root / "data/bus_information.csv"
    if not path.is_file():
        return {"rows": 0, "warning": "Reference CSV is unavailable."}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {"rows": len(rows), "duplicate_excess": len(rows) - len({tuple(row.items()) for row in rows}),
            "missing_destination": [row.get("Route number") for row in rows if not row.get("Destination", "").strip()],
            "warning": "Route endpoints do not establish visible EDS text, road names, or travel direction."}
