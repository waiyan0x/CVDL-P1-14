"""Create a stem-isolated, manifest-backed copy of the raw Roboflow v9 export.

This is a conservative split repair. Matching pre-Roboflow filename stems are
kept in one split, with test > valid > train priority. It does not certify that
different stems are independent scenes or that every annotation is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "training"
DEFAULT_SOURCE = DATA_DIR / "Front EDS.v9i.coco"
DEFAULT_OUTPUT = DATA_DIR / "2026-11-25-roboflow-v9-stem-isolated"
SPLITS = ("train", "valid", "test")
EXPECTED_CATEGORIES = {
    1: "front_eds",
    2: "front_eds_destination",
    3: "front_eds_num",
    4: "front_eds_route",
}
ROBOFLOW_SUFFIX = re.compile(r"\.rf\.[0-9a-f]+\.[^.]+$", re.IGNORECASE)
VISUALLY_CONFIRMED_TRAIN_EXCLUSIONS = {
    "IMG20261022115957_jpg": "Same B3 priority-boarding sign and depot scene as test/photo_2026-10-22_13-26-55_jpg",
}


def source_stem(name: str) -> str:
    stem = ROBOFLOW_SUFFIX.sub("", name)
    if stem == name:
        raise ValueError(f"Unrecognized Roboflow filename: {name}")
    return stem


def copy_with_hash(source: Path, destination: Path) -> str:
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as incoming, destination.open("wb") as outgoing:
        for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
            outgoing.write(chunk)
            digest.update(chunk)
    shutil.copystat(source, destination)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> str:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def prepare(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    training_root = DATA_DIR.resolve()
    if not source.is_relative_to(training_root) or not output.is_relative_to(training_root):
        raise ValueError("Source and output must stay within data/training")
    if source == output or output.exists():
        raise FileExistsError(f"Output already exists or equals source: {output}")
    stage = output.with_name(output.name + ".staging")
    if not stage.is_relative_to(training_root) or stage.exists():
        raise FileExistsError(f"Staging path already exists: {stage}")

    datasets, stems = {}, {}
    for split in SPLITS:
        coco = source / split / "_annotations.coco.json"
        data = json.loads(coco.read_text(encoding="utf-8"))
        names = {row["id"]: row["name"] for row in data["categories"]}
        for category_id, name in EXPECTED_CATEGORIES.items():
            if names.get(category_id) != name:
                raise ValueError(f"{split}: unexpected COCO category {category_id}: {names.get(category_id)}")
        if {ann["category_id"] for ann in data["annotations"]} - EXPECTED_CATEGORIES.keys():
            raise ValueError(f"{split}: unexpected active category")
        image_names = [row["file_name"] for row in data["images"]]
        if len(image_names) != len(set(image_names)):
            raise ValueError(f"{split}: duplicate image filename")
        if any(Path(name).name != name or not (source / split / name).is_file() for name in image_names):
            raise ValueError(f"{split}: missing or invalid COCO image path")
        datasets[split] = data
        stems[split] = {source_stem(name) for name in image_names}

    overlaps = {
        "train_valid": len(stems["train"] & stems["valid"]),
        "train_test": len(stems["train"] & stems["test"]),
        "valid_test": len(stems["valid"] & stems["test"]),
    }
    held_out = stems["valid"] | stems["test"]
    decisions = []
    checksums = {}
    output_counts = {}
    stage.mkdir(parents=True)
    copied = 0
    for split in SPLITS:
        data = datasets[split]
        kept_images = []
        seen_test_stems = set()
        for image in data["images"]:
            name = image["file_name"]
            stem = source_stem(name)
            reason = None
            if split == "train" and stem in held_out:
                reason = "source_stem_in_holdout"
            elif split == "train" and stem in VISUALLY_CONFIRMED_TRAIN_EXCLUSIONS:
                reason = "visually_confirmed_scene_in_test"
            elif split == "valid" and stem in stems["test"]:
                reason = "source_stem_in_test"
            elif split == "test" and stem in seen_test_stems:
                reason = "repeated_source_stem_within_test"
            if reason:
                decisions.append({"split": split, "file_name": name, "source_stem": stem, "reason": reason})
                continue
            kept_images.append(image)
            if split == "test":
                seen_test_stems.add(stem)
            relative = Path(split) / name
            checksums[relative.as_posix()] = copy_with_hash(source / relative, stage / relative)
            copied += 1
            if copied % 500 == 0:
                print(f"Copied and hashed {copied} images", flush=True)

        kept_ids = {image["id"] for image in kept_images}
        retained = [ann for ann in data["annotations"] if ann["image_id"] in kept_ids]
        rewritten = dict(data, images=kept_images, annotations=retained)
        relative = Path(split) / "_annotations.coco.json"
        checksums[relative.as_posix()] = write_json(stage / relative, rewritten)
        output_counts[split] = {
            "images": len(kept_images),
            "boxes": len(retained),
            "zero_box_images": len(kept_ids - {ann["image_id"] for ann in retained}),
            "excluded_images": len(data["images"]) - len(kept_images),
        }

    for name in ("README.dataset.txt", "README.roboflow.txt"):
        checksums[name] = copy_with_hash(source / name, stage / name)
    audit = {
        "method": "Conservative Roboflow filename-stem grouping; test > valid > train",
        "source": str(source),
        "source_coco_sha256": {
            split: hashlib.sha256((source / split / "_annotations.coco.json").read_bytes()).hexdigest()
            for split in SPLITS
        },
        "original_images": {split: len(datasets[split]["images"]) for split in SPLITS},
        "overlapping_source_stems": overlaps,
        "output_counts": output_counts,
        "excluded": decisions,
        "cross_stem_visual_review": VISUALLY_CONFIRMED_TRAIN_EXCLUSIONS,
        "review_limit": (
            "Same stems can be distinct synthetic scenes; different stems can still share a scene. "
            "This automated rule is conservative and does not replace human source, annotation, or capture review."
        ),
    }
    checksums["split_isolation_audit.json"] = write_json(stage / "split_isolation_audit.json", audit)
    manifest = {
        "spec": {
            "recipe": "roboflow-v9-filename-stem-isolation-v1",
            "source": str(source),
            "human_source_review": "pending",
            "human_annotation_review": "pending",
        },
        "checksums": dict(sorted(checksums.items())),
    }
    write_json(stage / "preparation_manifest.json", manifest)
    stage.rename(output)
    return {"output": str(output), "overlaps": overlaps, "counts": output_counts,
            "excluded_images": len(decisions), "manifest_entries": len(checksums)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
