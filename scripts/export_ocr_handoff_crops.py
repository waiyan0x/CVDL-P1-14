"""Export reviewed-v4 train or validation EDS crops for the OCR handoff."""

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.manifests import verify_export


CLASS_NAMES = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")
COCO_TO_MODEL = {1: 0, 3: 1, 4: 2, 2: 3}
DEFAULT_DATASET = ROOT / "data/training/2026-11-05-roboflow-v4-reviewed"
DEFAULT_CHECKPOINT = ROOT / ".runtime/object_detection_benchmark/01760a841333/runs/v4-reviewed-01/yolo11s/weights/best.pt"
DEFAULT_OUTPUT_PARENT = ROOT / ".runtime/ocr_handoff"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clip_box(box, width, height):
    x1, y1, x2, y2 = box
    left, top = max(0, min(width, int(x1))), max(0, min(height, int(y1)))
    right, bottom = max(0, min(width, int(np.ceil(x2)))), max(0, min(height, int(np.ceil(y2))))
    if right <= left or bottom <= top:
        raise ValueError(f"Invalid crop after clipping: {box}")
    return [left, top, right, bottom]


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def save_crop(image, box, output, kind, label, stem):
    relative = Path(kind) / label / f"{stem}.png"
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    image.crop(tuple(box)).save(target)
    return relative.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", choices=("train", "valid"), default="valid",
                        help="Train exports annotation crops only; validation also exports detector predictions.")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", type=Path, help="New output folder; defaults to .runtime/ocr_handoff/v4-reviewed-01-<split>.")
    parser.add_argument("--confidence", type=float, default=0.50)
    parser.add_argument("--nms-iou", type=float, default=0.70)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--zip", action="store_true", help="Create a portable ZIP next to the output folder.")
    args = parser.parse_args()
    default_output = DEFAULT_OUTPUT_PARENT / f"v4-reviewed-01-{'training' if args.split == 'train' else 'validation'}"
    dataset = args.dataset.resolve()
    checkpoint = args.checkpoint.resolve() if args.split == "valid" else None
    output = (args.output or default_output).resolve()
    if not 0 < args.confidence < 1 or not 0 < args.nms_iou < 1:
        parser.error("confidence and nms-iou must be between 0 and 1")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output already contains files: {output}")
    if checkpoint is not None and not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    manifest = verify_export(dataset)
    if manifest is None:
        raise ValueError("A verified dataset manifest is required")
    manifest_path = dataset / "preparation_manifest.json"
    coco_path = dataset / args.split / "_annotations.coco.json"
    coco = json.loads(coco_path.read_text(encoding="utf-8"))
    annotations = {}
    for ann in coco["annotations"]:
        annotations.setdefault(ann["image_id"], []).append(ann)

    model = None
    device = None
    if checkpoint is not None:
        os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".runtime/ultralytics"))
        import torch
        from ultralytics import YOLO

        model = YOLO(str(checkpoint))
        names = model.names
        actual = tuple(names[i] for i in range(4))
        if actual != CLASS_NAMES:
            raise ValueError(f"Checkpoint classes differ: {actual}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
    output.mkdir(parents=True, exist_ok=True)
    records, transcription_rows = [], []
    counts = Counter()

    for image_index, info in enumerate(sorted(coco["images"], key=lambda row: row["file_name"]), 1):
        image_path = (dataset / args.split / info["file_name"]).resolve()
        if not image_path.is_relative_to((dataset / args.split).resolve()):
            raise ValueError(f"Image escaped {args.split} folder: {info['file_name']}")
        with Image.open(image_path) as opened:
            image = opened.convert("RGB")
        if image.size != (info["width"], info["height"]):
            raise ValueError(f"COCO dimensions mismatch: {info['file_name']}")
        prefix = f"{image_index:03d}_{image_path.stem}"
        gt_entries = []
        for ann in sorted(annotations.get(info["id"], []), key=lambda row: row["id"]):
            class_id = COCO_TO_MODEL[ann["category_id"]]
            x, y, w, h = ann["bbox"]
            box = clip_box([x, y, x + w, y + h], *image.size)
            label = CLASS_NAMES[class_id]
            crop = save_crop(image, box, output, "ground_truth", label, f"{prefix}_a{ann['id']}")
            entry = {"annotation_id": ann["id"], "class_id": class_id, "label": label,
                     "box_xyxy": box, "crop": crop}
            gt_entries.append(entry)
            counts[f"gt_{label}"] += 1
            if class_id != 0:
                transcription_rows.append({"crop": crop, "image": info["file_name"],
                                            "label": label, "transcription": "", "review_status": "pending",
                                            "annotation_id": ann["id"],
                                            "source_name": info.get("extra", {}).get("name", ""),
                                            "reviewer": "", "reviewed_at": "", "legibility": "",
                                            "exclusion_reason": ""})

        predicted = []
        if model is not None:
            result = model.predict(np.asarray(image)[:, :, ::-1].copy(),
                                   imgsz=args.image_size, conf=args.confidence, iou=args.nms_iou,
                                   classes=list(range(4)), max_det=100, device=device, verbose=False)[0]
            for pred_index, box in enumerate(result.boxes):
                class_id = int(box.cls.item())
                xyxy = clip_box(box.xyxy[0].tolist(), *image.size)
                label = CLASS_NAMES[class_id]
                crop = save_crop(image, xyxy, output, "predicted", label, f"{prefix}_p{pred_index:03d}")
                candidates = [(entry["annotation_id"], iou(xyxy, entry["box_xyxy"]))
                              for entry in gt_entries if entry["class_id"] == class_id]
                match_id, overlap = max(candidates, key=lambda pair: pair[1]) if candidates else (None, 0.0)
                predicted.append({"class_id": class_id, "label": label, "box_xyxy": xyxy,
                                  "confidence": round(float(box.conf.item()), 6), "crop": crop,
                                  "matched_gt_annotation_id_at_iou50": match_id if overlap >= 0.5 else None,
                                  "best_same_class_iou": round(overlap, 6)})
                counts[f"pred_{label}"] += 1
        if not gt_entries:
            counts["negative_images"] += 1
            if model is not None:
                counts["predictions_on_negative_images"] += len(predicted)
        records.append({"image": info["file_name"], "image_id": info["id"],
                        "source_name": info.get("extra", {}).get("name", ""),
                        "image_sha256": sha256(image_path), "width": image.width, "height": image.height,
                        "ground_truth": gt_entries, "predictions": predicted})
        print(f"{image_index}/{len(coco['images'])}: {info['file_name']} | GT {len(gt_entries)} | predicted {len(predicted)}", flush=True)

    metadata = {"dataset": str(dataset), "split": args.split, "dataset_manifest_sha256": sha256(manifest_path),
                "coco_sha256": sha256(coco_path), "checkpoint": str(checkpoint) if checkpoint else None,
                "checkpoint_sha256": sha256(checkpoint) if checkpoint else None,
                "model": "yolo11s" if checkpoint else None, "device": device,
                "confidence": args.confidence if checkpoint else None,
                "nms_iou": args.nms_iou if checkpoint else None,
                "image_size": args.image_size if checkpoint else None,
                "image_count": len(records), "counts": dict(sorted(counts.items())), "images": records}
    if args.split == "valid":
        metadata["validation_coco_sha256"] = metadata["coco_sha256"]
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    with (output / "transcriptions_template.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["crop", "image", "label", "transcription", "review_status",
                                                     "annotation_id", "source_name", "reviewer", "reviewed_at",
                                                     "legibility", "exclusion_reason"])
        writer.writeheader()
        writer.writerows(transcription_rows)
    prediction_description = (
        f"`predicted/` contains YOLO11s crops at confidence {args.confidence:.2f} "
        f"and NMS IoU {args.nms_iou:.2f}. " if model is not None else
        "Training export has no detector predictions. "
    )
    (output / "README.md").write_text(
        f"# OCR handoff: reviewed v4 {args.split} crops\n\n"
        f"`ground_truth/` contains tight crops from COCO annotations. {prediction_description}Panel crops are context; text OCR should primarily use number, route and destination.\n\n"
        "`manifest.json` links each crop to its source image, coordinates, class and source name. For predicted crops it also records prediction confidence and diagnostic same-class IoU, neither of which proves readable or correct text. `transcriptions_template.csv` lists annotation-based text crops with blank transcription and reviewer fields: a human must review crops and enter verified text before CER, word error or exact-text accuracy can be reported.\n\n"
        f"The crop geometry has no padding or resizing. Keep train, validation and held-out test separate; this package uses {args.split} only. Source-name groups are a starting point for overlap review, not proof of scene independence. Do not use the detector's final test for tuning.\n\n"
        "Dataset images, crops and checkpoint are local artifacts and not automatically included in Git. The ZIP beside this folder can be transferred directly.\n",
        encoding="utf-8")
    if args.zip:
        zip_path = output.with_suffix(".zip")
        if zip_path.exists():
            raise FileExistsError(zip_path)
        shutil.make_archive(str(output), "zip", root_dir=output)
        print(f"ZIP: {zip_path}")
    print(f"Saved {len(records)} {args.split} images; {sum(v for k, v in counts.items() if k.startswith('gt_'))} GT crops; "
          f"{sum(v for k, v in counts.items() if k.startswith('pred_'))} predicted crops. Output: {output}")


if __name__ == "__main__":
    main()
