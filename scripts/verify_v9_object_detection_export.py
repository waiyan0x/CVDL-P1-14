"""Verify the prepared v9 COCO export without importing the model stack."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/training/2026-11-25-roboflow-v9-stem-isolated"
SPLITS = ("train", "valid", "test")
STEM_SUFFIX = re.compile(r"\.rf\.[0-9a-f]+\.[^.]+$", re.IGNORECASE)
CLASSES = {1: "front_eds", 2: "front_eds_destination", 3: "front_eds_num", 4: "front_eds_route"}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    root = DATASET.resolve()
    manifest_path = root / "preparation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checksums = manifest["checksums"]
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != manifest_path}
    if actual != set(checksums):
        raise ValueError(f"Manifest file list mismatch: missing={len(set(checksums)-actual)}, extra={len(actual-set(checksums))}")

    stems = {}
    file_digests = {}
    report = {}
    for split in SPLITS:
        data = json.loads((root / split / "_annotations.coco.json").read_text(encoding="utf-8"))
        classes = {row["id"]: row["name"] for row in data["categories"]}
        if any(classes.get(category_id) != name for category_id, name in CLASSES.items()):
            raise ValueError(f"{split}: wrong class mapping")
        images = {row["id"]: row for row in data["images"]}
        if len(images) != len(data["images"]):
            raise ValueError(f"{split}: duplicate COCO image ID")
        if len({row["file_name"] for row in data["images"]}) != len(images):
            raise ValueError(f"{split}: duplicate COCO filename")
        annotation_ids = [row["id"] for row in data["annotations"]]
        if len(annotation_ids) != len(set(annotation_ids)):
            raise ValueError(f"{split}: duplicate annotation ID")
        positives = set()
        for annotation in data["annotations"]:
            image = images.get(annotation["image_id"])
            if image is None or annotation["category_id"] not in CLASSES:
                raise ValueError(f"{split}: orphan annotation or unknown class")
            x, y, width, height = annotation["bbox"]
            if not all(math.isfinite(v) for v in (x, y, width, height)):
                raise ValueError(f"{split}: non-finite box")
            if width <= 0 or height <= 0 or x < -0.01 or y < -0.01 or x+width > image["width"]+0.01 or y+height > image["height"]+0.01:
                raise ValueError(f"{split}: invalid box for {image['file_name']}")
            positives.add(annotation["image_id"])

        stems[split] = set()
        file_digests[split] = set()
        for index, image in enumerate(data["images"], 1):
            name = image["file_name"]
            if Path(name).name != name:
                raise ValueError(f"{split}: invalid filename {name}")
            path = root / split / name
            relative = path.relative_to(root).as_posix()
            digest = sha256(path)
            if digest != checksums[relative]:
                raise ValueError(f"Checksum mismatch: {relative}")
            with Image.open(path) as opened:
                if opened.size != (image["width"], image["height"]):
                    raise ValueError(f"Image dimension mismatch: {relative}")
                if opened.getexif().get(274, 1) != 1:
                    raise ValueError(f"EXIF orientation mismatch: {relative}")
            stem = STEM_SUFFIX.sub("", name)
            if stem == name:
                raise ValueError(f"Unrecognized filename: {relative}")
            stems[split].add(stem)
            file_digests[split].add(digest)
            if index % 1000 == 0:
                print(f"Verified {split}: {index} images", flush=True)
        report[split] = {"images": len(images), "boxes": len(annotation_ids),
                         "zero_box_images": len(images) - len(positives)}

    for relative, expected in checksums.items():
        if relative.rsplit("/", 1)[-1] == "_annotations.coco.json" or "/" not in relative:
            if sha256(root / relative) != expected:
                raise ValueError(f"Checksum mismatch: {relative}")
    for a, b in (("train", "valid"), ("train", "test"), ("valid", "test")):
        if stems[a] & stems[b]:
            raise ValueError(f"Source stems cross {a}/{b}: {len(stems[a]&stems[b])}")
        if file_digests[a] & file_digests[b]:
            raise ValueError(f"Exact file bytes cross {a}/{b}: {len(file_digests[a]&file_digests[b])}")
    print(json.dumps({"verified": True, "manifest_files": len(checksums), "splits": report,
                      "cross_split_source_stems": 0, "cross_split_exact_file_duplicates": 0}, indent=2))


if __name__ == "__main__":
    main()
