"""Train one EDS detector from pretrained weights in a new, isolated run."""

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import sys
import time
from pathlib import Path


os.environ.setdefault("USE_TF", "0")
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

    view_root = Path(os.environ.get("EDS_YOLO_VIEW_ROOT", output_root)).resolve()
    view = view_root / fingerprint[:12] / "yolo"
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
    pretrained_root = Path(os.environ.get("EDS_PRETRAINED_ROOT", output_root / "pretrained")).resolve()
    pretrained = pretrained_root / f"{args.model}.pt"
    if not pretrained.is_file():
        raise FileNotFoundError(f"Published starting weight missing: {pretrained}")
    variant_settings = {
        "baseline": {"translate": 0.0, "scale": 0.0, "hsv_v": 0.0, "box": 7.5},
        "gentle_aug": {"translate": 0.02, "scale": 0.10, "hsv_v": 0.08, "box": 7.5},
        "localization": {"translate": 0.0, "scale": 0.0, "hsv_v": 0.0, "box": 8.5},
    }[args.variant]
    model = YOLO(str(pretrained))
    started = time.perf_counter()
    try:
        model.train(
            data=str(data_yaml), epochs=args.epochs, imgsz=args.image_size,
            batch=args.batch_size, seed=args.seed, deterministic=True,
            project=str(run_dir.parent), name=run_dir.name, exist_ok=False,
            device=device, workers=args.workers, patience=15, mosaic=0.0, mixup=0.0,
            copy_paste=0.0, degrees=0.0, translate=variant_settings["translate"],
            scale=variant_settings["scale"], fliplr=0.0, hsv_h=0.0, hsv_s=0.0,
            hsv_v=variant_settings["hsv_v"], box=variant_settings["box"],
            cls=0.5, dfl=1.5,
        )
        actual_dir = Path(model.trainer.save_dir)
        if actual_dir != run_dir:
            raise RuntimeError(f"Ultralytics chose an unexpected run directory: {actual_dir}")
        if not (run_dir / "weights/best.pt").is_file():
            raise FileNotFoundError(run_dir / "weights/best.pt")
        (run_dir / "complete.txt").write_text("Fresh training completed.\n", encoding="utf-8")
    finally:
        # Preserve saved epochs and weights on normal completion or interruption.
        if run_dir.is_dir():
            (run_dir / "experiment.json").write_text(json.dumps({
                "model": run_dir.name, "published_starting_weight": str(pretrained),
                "variant": args.variant, "dataset_manifest_sha256": fingerprint,
                "run_id": args.run_id, "epochs_cap": args.epochs,
                "image_size": args.image_size, "batch_size": args.batch_size,
                "workers": args.workers, "seed": args.seed,
                "training_seconds": time.perf_counter() - started,
                "variant_settings": variant_settings,
            }, indent=2) + "\n", encoding="utf-8")
            archive_yolo_run(ROOT, fingerprint, run_dir.name, run_dir, args.run_id)


class DetrCocoDataset:
    """Process one COCO image in a DataLoader worker."""

    def __init__(self, rows, processor, image_size):
        self.rows = rows
        self.processor = processor
        self.image_size = image_size

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        from PIL import Image

        row = self.rows[index]
        with Image.open(row["path"]) as opened:
            image = opened.convert("RGB")
        annotations = [
            {"id": ann["id"], "image_id": row["image"]["id"],
             "category_id": COCO_TO_INDEX[ann["category_id"]],
             "bbox": ann["bbox"], "area": ann["bbox"][2] * ann["bbox"][3],
             "iscrowd": 0}
            for ann in row["annotations"]
        ]
        encoded = self.processor(
            images=image,
            annotations={"image_id": row["image"]["id"], "annotations": annotations},
            size={"shortest_edge": self.image_size, "longest_edge": self.image_size},
            return_tensors="pt",
        )
        return {"pixel_values": encoded["pixel_values"][0], "labels": encoded["labels"][0]}


def collate_detr_batch(samples):
    """Pad variable image sizes while retaining per-image DETR labels."""
    import torch

    height = max(sample["pixel_values"].shape[-2] for sample in samples)
    width = max(sample["pixel_values"].shape[-1] for sample in samples)
    pixels = torch.zeros((len(samples), 3, height, width), dtype=samples[0]["pixel_values"].dtype)
    pixel_mask = torch.zeros((len(samples), height, width), dtype=torch.long)
    for index, sample in enumerate(samples):
        image = sample["pixel_values"]
        h, w = image.shape[-2:]
        pixels[index, :, :h, :w] = image
        pixel_mask[index, :h, :w] = 1
    return {"pixel_values": pixels, "pixel_mask": pixel_mask,
            "labels": [sample["labels"] for sample in samples]}


def train_detr_accumulated(args, splits, fingerprint, run_dir, device, model, processor, optimizer):
    """Use loader workers and gradient accumulation for the requested effective batch."""
    import torch
    from torch.utils.data import DataLoader

    (run_dir / "train").mkdir(parents=True)
    settings = {
        "model": "detr-resnet-50", "pretrained": "facebook/detr-resnet-50",
        "dataset_manifest_sha256": fingerprint, "run_id": args.run_id,
        "epochs": args.epochs, "image_size": args.image_size, "seed": args.seed,
        "effective_batch_size": args.batch_size,
        "gpu_micro_batch_size": args.micro_batch_size,
        "gradient_accumulation_steps": args.batch_size // args.micro_batch_size,
        "train_loader_workers": args.workers, "validation_loader_workers": 0,
        "optimizer": "AdamW", "learning_rate": 1e-5, "weight_decay": 1e-4,
        "shuffle": False,
    }
    (run_dir / "train/settings.json").write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    train_data = DetrCocoDataset(splits["train"]["rows"], processor, args.image_size)
    valid_data = DetrCocoDataset(splits["valid"]["rows"], processor, args.image_size)
    loader_options = {"batch_size": args.micro_batch_size, "collate_fn": collate_detr_batch,
                      "pin_memory": device == "cuda"}
    train_loader = DataLoader(train_data, shuffle=False, num_workers=args.workers,
                              persistent_workers=args.workers > 0, **loader_options)
    valid_loader = DataLoader(valid_data, shuffle=False, num_workers=0, **loader_options)

    def on_device(batch):
        return {"pixel_values": batch["pixel_values"].to(device, non_blocking=True),
                "pixel_mask": batch["pixel_mask"].to(device, non_blocking=True),
                "labels": [{key: value.to(device, non_blocking=True) for key, value in label.items()}
                           for label in batch["labels"]]}

    best_loss, history = float("inf"), []
    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        train_total = processed = window_images = 0
        window_target = min(args.batch_size, len(train_data))
        for batch in train_loader:
            count = len(batch["labels"])
            loss = model(**on_device(batch)).loss
            (loss * (count / window_target)).backward()
            train_total += float(loss.detach().cpu()) * count
            processed += count
            window_images += count
            if window_images == window_target:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                window_images = 0
                window_target = min(args.batch_size, len(train_data) - processed)
        model.eval()
        valid_total = valid_count = 0
        with torch.inference_mode():
            for batch in valid_loader:
                count = len(batch["labels"])
                valid_total += float(model(**on_device(batch)).loss.detach().cpu()) * count
                valid_count += count
        record = {"epoch": epoch, "train_loss": train_total / processed,
                  "valid_loss": valid_total / valid_count}
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


def train_detr(args, splits, fingerprint, run_dir, device):
    import torch
    from PIL import Image
    from transformers import DetrForObjectDetection, DetrImageProcessor

    if args.use_detr_loader:
        torch.manual_seed(args.seed)
        if device == "cuda":
            torch.cuda.manual_seed_all(args.seed)
    processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model = DetrForObjectDetection.from_pretrained(
        "facebook/detr-resnet-50", num_labels=4,
        id2label=INDEX_TO_NAME,
        label2id={name: index for index, name in INDEX_TO_NAME.items()},
        ignore_mismatched_sizes=True,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=1e-4)
    if args.use_detr_loader:
        return train_detr_accumulated(args, splits, fingerprint, run_dir, device,
                                      model, processor, optimizer)

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


def output_root_for(dataset):
    """Route the named v9 export and its backups to local, versioned folders."""
    if dataset.name == "2026-11-25-roboflow-v9-stem-isolated":
        output_root = (ROOT / "Object-Detection-v9/object_detection").resolve()
        os.environ["EDS_OUTPUT_ROOT"] = str(output_root)
        os.environ["EDS_ARCHIVE_ROOT"] = str(output_root)
        os.environ["EDS_YOLO_BACKUP_ROOT"] = str(ROOT / "YOLO_Weights/v9")
        os.environ["EDS_YOLO_VIEW_ROOT"] = str(ROOT / ".runtime/object_detection_benchmark")
        os.environ["EDS_PRETRAINED_ROOT"] = str(ROOT / ".runtime/object_detection_benchmark/pretrained")
        return output_root
    return Path(os.environ.get("EDS_OUTPUT_ROOT", ROOT / ".runtime/object_detection_benchmark")).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("yolo11n", "yolo11s", "detr-resnet-50"))
    parser.add_argument("--variant", choices=("baseline", "gentle_aug", "localization"),
                        default="baseline", help="Fresh YOLO v9 A/B experiment; DETR uses baseline only")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/training/2026-10-30-torchvision")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--micro-batch-size", type=int, default=2,
                        help="DETR images per GPU step; --batch-size is the accumulated effective batch")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    is_v9 = args.dataset.resolve().name == "2026-11-25-roboflow-v9-stem-isolated"
    args.use_detr_loader = is_v9
    if args.batch_size is None:
        args.batch_size = 32 if is_v9 else 4
    if args.workers is None:
        args.workers = 4 if is_v9 else 0
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.run_id):
        parser.error("--run-id may contain only letters, digits, underscores and hyphens")
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 32 or args.workers < 0:
        parser.error("epochs, batch size and image size must be positive; workers cannot be negative")
    if args.model == "detr-resnet-50" and args.use_detr_loader and (
            args.micro_batch_size < 1 or args.batch_size % args.micro_batch_size):
        parser.error("For v9 DETR, micro batch size must be positive and divide the effective batch size")
    if args.variant != "baseline" and (not is_v9 or not args.model.startswith("yolo")):
        parser.error("YOLO A/B variants require a YOLO model and the named verified v9 dataset")
    if args.variant == "gentle_aug" and args.image_size != 640:
        parser.error("Gentle augmentation A requires image size 640")
    if args.variant == "localization" and args.image_size != 800:
        parser.error("Localization B requires image size 800")
    dataset = args.dataset.resolve()
    splits, fingerprint = verified_dataset(dataset)
    output_root = output_root_for(dataset)
    run_name = args.model if args.variant == "baseline" else f"{args.model}-{args.variant}"
    run_dir = output_root / fingerprint[:12] / "runs" / args.run_id / run_name
    if run_dir.exists():
        raise FileExistsError(f"Run already exists: {run_dir}. Choose a new --run-id.")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print({"model": args.model, "variant": args.variant, "run_id": args.run_id, "device": device,
           "batch_size": args.batch_size, "workers": args.workers,
           "detr_micro_batch_size": args.micro_batch_size if args.model == "detr-resnet-50" and is_v9 else None,
           "dataset": str(dataset), "run_dir": str(run_dir)}, flush=True)
    started = time.perf_counter()
    if args.model.startswith("yolo"):
        train_yolo(args, splits, fingerprint, output_root, run_dir, device)
    else:
        train_detr(args, splits, fingerprint, run_dir, device)
    print(f"Completed in {time.perf_counter() - started:.1f}s: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
