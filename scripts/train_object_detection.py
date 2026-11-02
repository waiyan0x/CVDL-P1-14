"""Train one EDS detector from pretrained weights in a new, isolated run."""

import argparse
import hashlib
import re
import shutil
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.datasets import load_coco_splits
from data_preparation.manifests import verify_export
from object_detection_artifacts import archive_detr_epoch, archive_yolo_run


CLASS_NAMES = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")
COCO_TO_INDEX = {1: 0, 3: 1, 4: 2, 2: 3}
INDEX_TO_NAME = dict(enumerate(CLASS_NAMES))


def verified_dataset(dataset):
    if not dataset.is_dir():
        raise FileNotFoundError(dataset)
    if verify_export(dataset) is None:
        raise ValueError("A verified dataset manifest is required.")
    splits = load_coco_splits(dataset)
    for split_name, split in splits.items():
        categories = {category["id"]: category["name"] for category in split["data"]["categories"]}
        for coco_id, index in COCO_TO_INDEX.items():
            if categories.get(coco_id) != CLASS_NAMES[index]:
                raise ValueError(f"{split_name}: wrong category mapping for COCO ID {coco_id}")
        unexpected = {a["category_id"] for a in split["data"]["annotations"]} - set(COCO_TO_INDEX)
        if unexpected:
            raise ValueError(f"{split_name}: unexpected category IDs {unexpected}")
    manifest = next(
        (dataset / name for name in ("augmentation_manifest.json", "preparation_manifest.json")
         if (dataset / name).is_file()), None
    )
    if manifest is None:
        raise FileNotFoundError("Dataset manifest missing")
    return splits, hashlib.sha256(manifest.read_bytes()).hexdigest()


def yolo_view(splits, fingerprint, output_root):
    import yaml
    from PIL import Image

    view = output_root / fingerprint[:12] / "yolo"
    config = view / "data.yaml"
    if config.is_file():
        return config
    if view.exists():
        raise FileExistsError(f"Incomplete YOLO conversion: {view}")
    for split_name, split in splits.items():
        image_dir, label_dir = view / "images" / split_name, view / "labels" / split_name
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        for row in split["rows"]:
            source = row["path"]
            with Image.open(source) as opened:
                needs_png = opened.format == "AVIF" or source.suffix.lower() not in (
                    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"
                )
                name = source.stem + ".png" if needs_png else source.name
                image_target = image_dir / name
                label_target = label_dir / (source.stem + ".txt")
                if image_target.exists() or label_target.exists():
                    raise ValueError(f"Duplicate output stem in {split_name}: {source.stem}")
                if needs_png:
                    opened.convert("RGB").save(image_target, format="PNG")
                else:
                    shutil.copy2(source, image_target)
            width, height = row["image"]["width"], row["image"]["height"]
            labels = []
            for annotation in row["annotations"]:
                x, y, w, h = annotation["bbox"]
                index = COCO_TO_INDEX[annotation["category_id"]]
                labels.append(
                    f"{index} {(x+w/2)/width:.8f} {(y+h/2)/height:.8f} {w/width:.8f} {h/height:.8f}"
                )
            label_target.write_text("\n".join(labels) + ("\n" if labels else ""), encoding="utf-8")
    config.write_text(yaml.safe_dump({
        "path": str(view), "train": "images/train", "val": "images/valid",
        "test": "images/test", "names": INDEX_TO_NAME,
    }, sort_keys=False), encoding="utf-8")
    return config


def train_yolo(args, splits, fingerprint, output_root, run_dir, device):
    from ultralytics import YOLO

    data_yaml = yolo_view(splits, fingerprint, output_root)
    pretrained = output_root / "pretrained" / f"{args.model}.pt"
    model = YOLO(str(pretrained))
    model.train(
        data=str(data_yaml), epochs=args.epochs, imgsz=args.image_size,
        batch=args.batch_size, seed=args.seed, deterministic=True,
        project=str(run_dir.parent), name=args.model, exist_ok=False,
        device=device, workers=0, patience=10, mosaic=0.0, mixup=0.0,
        copy_paste=0.0, degrees=0.0, translate=0.0, scale=0.0,
        fliplr=0.0, hsv_h=0.0, hsv_s=0.0, hsv_v=0.0,
    )
    actual_dir = Path(model.trainer.save_dir)
    if actual_dir != run_dir:
        raise RuntimeError(f"Ultralytics chose an unexpected run directory: {actual_dir}")
    if not (run_dir / "weights/best.pt").is_file():
        raise FileNotFoundError(run_dir / "weights/best.pt")
    (run_dir / "complete.txt").write_text("Fresh training completed.\n", encoding="utf-8")
    archive_yolo_run(ROOT, fingerprint, args.model, run_dir, args.run_id)


def train_detr(args, splits, fingerprint, run_dir, device):
    import torch
    from PIL import Image
    from transformers import DetrForObjectDetection, DetrImageProcessor

    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model = DetrForObjectDetection.from_pretrained(
        "facebook/detr-resnet-50", num_labels=4,
        id2label=INDEX_TO_NAME,
        label2id={name: index for index, name in INDEX_TO_NAME.items()},
        ignore_mismatched_sizes=True,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=1e-4)

    def item(row):
        with Image.open(row["path"]) as opened:
            image = opened.convert("RGB")
        annotations = [
            {"id": ann["id"], "image_id": row["image"]["id"],
             "category_id": COCO_TO_INDEX[ann["category_id"]],
             "bbox": ann["bbox"], "area": ann["bbox"][2] * ann["bbox"][3],
             "iscrowd": 0}
            for ann in row["annotations"]
        ]
        encoded = processor(
            images=image,
            annotations={"image_id": row["image"]["id"], "annotations": annotations},
            size={"shortest_edge": args.image_size, "longest_edge": args.image_size},
            return_tensors="pt",
        )
        return {
            "pixel_values": encoded["pixel_values"].to(device),
            "pixel_mask": encoded["pixel_mask"].to(device),
            "labels": [{key: value.to(device) for key, value in encoded["labels"][0].items()}],
        }

    best_loss, history = float("inf"), []
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses = []
        for row in splits["train"]["rows"]:
            batch = item(row)
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
        model.eval()
        valid_losses = []
        with torch.inference_mode():
            for row in splits["valid"]["rows"]:
                valid_losses.append(float(model(**item(row)).loss.detach().cpu()))
        record = {"epoch": epoch, "train_loss": statistics.mean(train_losses),
                  "valid_loss": statistics.mean(valid_losses)}
        history.append(record)
        print(record, flush=True)
        if record["valid_loss"] < best_loss:
            best_loss = record["valid_loss"]
            run_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(run_dir)
            processor.save_pretrained(run_dir)
        archive_detr_epoch(ROOT, fingerprint, history, run_dir if run_dir.is_dir() else None, args.run_id)
    (run_dir / "complete.txt").write_text("Fresh training completed.\n", encoding="utf-8")
    archive_detr_epoch(ROOT, fingerprint, history, run_dir, args.run_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("yolo11n", "yolo11s", "detr-resnet-50"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/training/2026-10-30-torchvision")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("--run-id may contain only letters, digits, underscores and hyphens")
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 32:
        parser.error("epochs, batch size and image size must be positive")
    dataset = args.dataset.resolve()
    splits, fingerprint = verified_dataset(dataset)
    output_root = ROOT / ".runtime/object_detection_benchmark"
    run_dir = output_root / fingerprint[:12] / "runs" / args.run_id / args.model
    if run_dir.exists():
        raise FileExistsError(f"Run already exists: {run_dir}. Choose a new --run-id.")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print({"model": args.model, "run_id": args.run_id, "device": device,
           "dataset": str(dataset), "run_dir": str(run_dir)}, flush=True)
    started = time.perf_counter()
    if args.model.startswith("yolo"):
        train_yolo(args, splits, fingerprint, output_root, run_dir, device)
    else:
        train_detr(args, splits, fingerprint, run_dir, device)
    print(f"Completed in {time.perf_counter() - started:.1f}s: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
