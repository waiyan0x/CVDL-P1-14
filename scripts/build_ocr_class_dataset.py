"""Create split/class OCR crops from a verified COCO detector export."""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.manifests import verify_export

from export_ocr_handoff_crops import CLASS_NAMES, COCO_TO_MODEL, clip_box

SPLITS = ("train", "valid", "test")
FIELDS = ("crop", "image", "image_sha256", "source_name", "annotation_id", "label",
          "transcription", "review_status", "reviewer", "reviewed_at", "legibility",
          "exclusion_reason")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "data/training/2026-11-05-roboflow-v4-reviewed")
    parser.add_argument("--output", type=Path,
                        default=ROOT / ".runtime/ocr_class_dataset/v4-reviewed-01")
    args = parser.parse_args()
    dataset, output = args.dataset.resolve(), args.output.resolve()
    if output == dataset or output.is_relative_to(dataset):
        parser.error("Output must be outside the frozen detector dataset")
    if output.exists() and any(output.iterdir()):
        parser.error(f"Output is not empty: {output}")
    if verify_export(dataset) is None:
        parser.error("A verified dataset manifest is required")

    manifest = {"schema_version": 1, "source_dataset": str(dataset),
                "source_manifest_sha256": sha256(dataset / "preparation_manifest.json"),
                "class_names": list(CLASS_NAMES), "splits": {}}
    for split in SPLITS:
        folder = dataset / split
        coco_path = folder / "_annotations.coco.json"
        coco = json.loads(coco_path.read_text(encoding="utf-8"))
        image_ids = {item["id"] for item in coco["images"]}
        annotations = {}
        for annotation in coco["annotations"]:
            if annotation["image_id"] not in image_ids or annotation["category_id"] not in COCO_TO_MODEL:
                raise ValueError(f"Unknown image or class in {coco_path}")
            annotations.setdefault(annotation["image_id"], []).append(annotation)
        split_root = output / split
        for class_name in CLASS_NAMES:
            (split_root / class_name).mkdir(parents=True, exist_ok=True)
        rows, records, negatives = [], [], []
        for index, info in enumerate(sorted(coco["images"], key=lambda x: x["file_name"]), 1):
            image_path = (folder / info["file_name"]).resolve()
            if not image_path.is_relative_to(folder.resolve()):
                raise ValueError(f"Image escaped {split} folder: {info['file_name']}")
            image_hash = sha256(image_path)
            source_name = info.get("extra", {}).get("name", "")
            with Image.open(image_path) as opened:
                image = opened.convert("RGB")
            if image.size != (info["width"], info["height"]):
                raise ValueError(f"COCO dimensions differ from {image_path}")
            image_annotations = sorted(annotations.get(info["id"], []), key=lambda a: a["id"])
            if not image_annotations:
                negatives.append(info["file_name"])
            for annotation in image_annotations:
                label = CLASS_NAMES[COCO_TO_MODEL[annotation["category_id"]]]
                x, y, width, height = annotation["bbox"]
                box = clip_box((x, y, x + width, y + height), *image.size)
                relative = Path(split) / label / f"{index:03d}_{image_path.stem}_a{annotation['id']}.png"
                target = output / relative
                image.crop(tuple(box)).save(target)
                records.append({"crop": relative.as_posix(), "image": info["file_name"],
                                "image_sha256": image_hash, "source_name": source_name,
                                "annotation_id": annotation["id"], "label": label, "box_xyxy": box})
                if label != "front_eds":
                    rows.append({"crop": relative.as_posix(), "image": info["file_name"],
                                 "image_sha256": image_hash, "source_name": source_name,
                                 "annotation_id": annotation["id"], "label": label,
                                 "transcription": "", "review_status": "pending", "reviewer": "",
                                 "reviewed_at": "", "legibility": "", "exclusion_reason": ""})
        with (split_root / "transcriptions_template.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        manifest["splits"][split] = {"coco_sha256": sha256(coco_path), "images": len(coco["images"]),
                                     "negative_images": negatives, "crops": records,
                                     "text_crop_count": len(rows)}
        print(f"{split}: {len(coco['images'])} images, {len(records)} crops, {len(rows)} text rows")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# OCR crops by split and class\n\n"
        "Each `train/`, `valid/`, and `test/` folder has `front_eds`, `front_eds_num`, "
        "`front_eds_route`, and `front_eds_destination` subfolders. These are tight "
        "annotation-box crops, not full images. `front_eds` is panel context; the "
        "other three folders contain text fields. Negative images have no crop and "
        "are listed in `manifest.json`.\n\n"
        "Each split has a blank `transcriptions_template.csv`. Class folders and "
        "bounding boxes are not OCR text labels: a reviewer must transcribe visible "
        "text, record their name/date, and mark unreadable or excluded crops. Keep "
        "train for fitting, valid for selection, and test untouched until final "
        "evaluation. Source images and the verified COCO dataset are unchanged.\n",
        encoding="utf-8")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
