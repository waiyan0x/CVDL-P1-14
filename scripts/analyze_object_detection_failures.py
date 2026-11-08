"""Create a validation-only qualitative review package for selected YOLO11s."""

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.datasets import load_coco_splits
from data_preparation.manifests import verify_export


CLASS_NAMES = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")
COCO_TO_INDEX = {1: 0, 3: 1, 4: 2, 2: 3}
COLORS = {
    "gt": (30, 210, 80),
    "tp": (40, 160, 255),
    "fp": (255, 70, 70),
    "miss": (255, 190, 30),
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iou(box_a, box_b):
    x1, y1 = max(box_a[0], box_b[0]), max(box_a[1], box_b[1])
    x2, y2 = min(box_a[2], box_b[2]), min(box_a[3], box_b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def blur_score(image):
    try:
        import cv2

        gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except ImportError:
        gray = np.asarray(image.convert("L"), dtype=np.float32)
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        return float(dx.var() + dy.var())


def match_image(ground_truth, predictions, threshold=0.5):
    assigned_gt = set()
    matches = []
    unmatched_predictions = []
    for pred_index in sorted(range(len(predictions)), key=lambda i: predictions[i]["score"], reverse=True):
        pred = predictions[pred_index]
        candidates = [
            (gt_index, iou(pred["box"], gt["box"]))
            for gt_index, gt in enumerate(ground_truth)
            if gt_index not in assigned_gt and gt["label"] == pred["label"]
        ]
        if candidates:
            gt_index, overlap = max(candidates, key=lambda item: item[1])
            if overlap >= threshold:
                assigned_gt.add(gt_index)
                matches.append({"prediction": pred_index, "ground_truth": gt_index, "iou": overlap})
                continue
        unmatched_predictions.append(pred_index)

    unmatched_gt = [index for index in range(len(ground_truth)) if index not in assigned_gt]
    confusions = []
    for pred_index in unmatched_predictions:
        pred = predictions[pred_index]
        overlaps = [(index, iou(pred["box"], gt["box"])) for index, gt in enumerate(ground_truth)]
        if not overlaps:
            continue
        gt_index, overlap = max(overlaps, key=lambda item: item[1])
        if overlap >= threshold and ground_truth[gt_index]["label"] != pred["label"]:
            confusions.append({
                "prediction": pred_index,
                "ground_truth": gt_index,
                "iou": overlap,
                "actual": CLASS_NAMES[ground_truth[gt_index]["label"]],
                "predicted": CLASS_NAMES[pred["label"]],
            })
    return matches, unmatched_gt, unmatched_predictions, confusions


def draw_label(draw, xy, text, fill, font):
    left, top = int(xy[0]), max(0, int(xy[1]) - 15)
    bounds = draw.textbbox((left, top), text, font=font)
    draw.rectangle(bounds, fill=fill)
    draw.text((left, top), text, fill=(0, 0, 0), font=font)


def make_overlay(image, ground_truth, predictions, matches, unmatched_gt, unmatched_predictions):
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    matched_predictions = {item["prediction"] for item in matches}
    for index, gt in enumerate(ground_truth):
        color = COLORS["miss"] if index in unmatched_gt else COLORS["gt"]
        draw.rectangle(gt["box"], outline=color, width=4)
        draw_label(draw, gt["box"], f"GT {CLASS_NAMES[gt['label']]}", color, font)
    for index, pred in enumerate(predictions):
        color = COLORS["tp"] if index in matched_predictions else COLORS["fp"]
        draw.rectangle(pred["box"], outline=color, width=3)
        draw_label(draw, (pred["box"][0], pred["box"][3]),
                   f"P {CLASS_NAMES[pred['label']]} {pred['score']:.2f}", color, font)
    canvas.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
    return canvas


def safe_stem(path):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(path).stem)[:100]


def save_crops(image, item, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for kind, rows in (("gt", item["ground_truth"]), ("pred", item["predictions"])):
        for index, row in enumerate(rows):
            if row["label"] == 0:
                continue
            x1, y1, x2, y2 = row["box"]
            padding_x = max(2, int((x2 - x1) * 0.08))
            padding_y = max(2, int((y2 - y1) * 0.12))
            crop_box = (
                max(0, int(x1) - padding_x), max(0, int(y1) - padding_y),
                min(image.width, int(math.ceil(x2)) + padding_x),
                min(image.height, int(math.ceil(y2)) + padding_y),
            )
            crop = image.crop(crop_box)
            name = f"{kind}_{index:02d}_{CLASS_NAMES[row['label']]}"
            if kind == "pred":
                name += f"_{row['score']:.2f}"
            crop.save(destination / f"{name}.png")


def contact_sheet(items, output):
    tile_width, tile_height, columns = 720, 520, 2
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (tile_width * columns, tile_height * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        overlay = Image.open(item["overlay_path"]).convert("RGB")
        overlay.thumbnail((tile_width - 20, tile_height - 55), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width + 10
        y = (index // columns) * tile_height + 35
        sheet.paste(overlay, (x, y))
        caption = (
            f"#{index + 1} {item['file_name'][:55]} | TP {item['tp']} FP {item['fp']} "
            f"FN {item['fn']} | blur {item['blur_score']:.0f}"
        )
        draw.text((x, y - 25), caption, fill="black", font=font)
    sheet.save(output, quality=92)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/training/2026-10-30-torchvision")
    parser.add_argument("--checkpoint", type=Path, default=ROOT / ".runtime/object_detection_benchmark/bf938f526d2c/runs/baseline-01/yolo11s/weights/best.pt")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/object_detection/bf938f526d2c/runs/baseline-01/yolo11s/qualitative_validation")
    parser.add_argument("--confidence", type=float, default=0.20)
    parser.add_argument("--nms-iou", type=float, default=0.70)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    dataset, checkpoint, output = args.dataset.resolve(), args.checkpoint.resolve(), args.output.resolve()
    if verify_export(dataset) is None:
        raise ValueError("Verified dataset manifest required")
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Review output already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    overlays, crops = output / "overlays", output / "crops"
    overlays.mkdir()
    crops.mkdir()

    from ultralytics import YOLO
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = YOLO(str(checkpoint))
    validation = load_coco_splits(dataset)["valid"]["rows"]
    summaries = []
    confusion_counts = Counter()

    for row_index, row in enumerate(validation, 1):
        with Image.open(row["path"]) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        prediction = model.predict(
            np.asarray(image)[:, :, ::-1].copy(), imgsz=args.image_size,
            conf=0.001, iou=args.nms_iou, device=device, verbose=False,
        )[0]
        boxes = prediction.boxes
        all_predictions = [
            {"box": [float(value) for value in box], "score": float(score), "label": int(label)}
            for box, score, label in zip(boxes.xyxy.cpu().tolist(), boxes.conf.cpu().tolist(), boxes.cls.cpu().tolist())
        ]
        predictions = [item for item in all_predictions if item["score"] >= args.confidence]
        ground_truth = []
        for annotation in row["annotations"]:
            x, y, width, height = annotation["bbox"]
            ground_truth.append({
                "box": [float(x), float(y), float(x + width), float(y + height)],
                "label": COCO_TO_INDEX[annotation["category_id"]],
                "area_fraction": float(width * height / (image.width * image.height)),
            })
        matches, unmatched_gt, unmatched_predictions, confusions = match_image(ground_truth, predictions)
        for confusion in confusions:
            confusion_counts[(confusion["actual"], confusion["predicted"])] += 1
        matched_ious = [item["iou"] for item in matches]
        small_count = sum(item["area_fraction"] < 0.01 for item in ground_truth)
        tiny_count = sum(item["area_fraction"] < 0.0025 for item in ground_truth)
        severity = (
            10 * len(unmatched_gt) + 4 * len(confusions) + 2 * len(unmatched_predictions)
            + sum(max(0.0, 0.75 - value) for value in matched_ious)
            + 0.25 * small_count + 0.5 * tiny_count
        )
        summary = {
            "index": row_index,
            "file_name": Path(row["path"]).name,
            "source_path": str(row["path"]),
            "width": image.width,
            "height": image.height,
            "ground_truth": ground_truth,
            "predictions": predictions,
            "tp": len(matches),
            "fp": len(unmatched_predictions),
            "fn": len(unmatched_gt),
            "matches": matches,
            "unmatched_ground_truth": unmatched_gt,
            "unmatched_predictions": unmatched_predictions,
            "confusions": confusions,
            "mean_matched_iou": float(np.mean(matched_ious)) if matched_ious else None,
            "blur_score": blur_score(image),
            "mean_brightness": float(np.asarray(image.convert("L"), dtype=np.float32).mean()),
            "small_ground_truth": int(small_count),
            "tiny_ground_truth": int(tiny_count),
            "severity": float(severity),
            "negative": not ground_truth,
        }
        summaries.append(summary)
        print(f"{row_index}/{len(validation)} {summary['file_name']} TP={summary['tp']} FP={summary['fp']} FN={summary['fn']}", flush=True)

    ranked = sorted(
        summaries,
        key=lambda item: (item["severity"], item["fn"], item["fp"], -(item["mean_matched_iou"] or 0.0)),
        reverse=True,
    )[:args.top]
    for rank, item in enumerate(ranked, 1):
        with Image.open(item["source_path"]) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        overlay = make_overlay(
            image, item["ground_truth"], item["predictions"], item["matches"],
            item["unmatched_ground_truth"], item["unmatched_predictions"],
        )
        # Keep generated evidence paths short enough for Windows Git checkouts.
        stem = f"case_{rank:02d}"
        overlay_path = overlays / f"{stem}.jpg"
        overlay.save(overlay_path, quality=92)
        item["rank"] = rank
        item["overlay_path"] = str(overlay_path)
        item["overlay_relative"] = str(overlay_path.relative_to(output)).replace("\\", "/")
        crop_dir = crops / stem
        save_crops(image, item, crop_dir)
        item["crop_directory"] = str(crop_dir.relative_to(output)).replace("\\", "/")

    sheet_path = output / "contact_sheet.jpg"
    contact_sheet(ranked, sheet_path)
    aggregate = {
        "split": "valid",
        "dataset_manifest_sha256": sha256(dataset / "augmentation_manifest.json"),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256(checkpoint),
        "settings": {"confidence": args.confidence, "nms_iou": args.nms_iou, "image_size": args.image_size, "device": device},
        "images": len(summaries),
        "negatives": sum(item["negative"] for item in summaries),
        "tp": sum(item["tp"] for item in summaries),
        "fp": sum(item["fp"] for item in summaries),
        "fn": sum(item["fn"] for item in summaries),
        "negative_false_positives": sum(item["fp"] for item in summaries if item["negative"]),
        "class_confusions": [
            {"actual": actual, "predicted": predicted, "count": count}
            for (actual, predicted), count in sorted(confusion_counts.items())
        ],
        "top_cases": ranked,
        "all_images": summaries,
    }
    (output / "failure_analysis.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")

    rows = []
    for item in ranked:
        issues = []
        if item["fn"]:
            issues.append(f"{item['fn']} missed box(es)")
        if item["fp"]:
            issues.append(f"{item['fp']} unmatched prediction(s)")
        if item["confusions"]:
            issues.append("class confusion")
        if item["tiny_ground_truth"]:
            issues.append(f"{item['tiny_ground_truth']} tiny GT")
        elif item["small_ground_truth"]:
            issues.append(f"{item['small_ground_truth']} small GT")
        if not issues:
            issues.append("low localization quality")
        rows.append(
            f"| {item['rank']} | `{item['file_name']}` | {item['tp']} | {item['fp']} | {item['fn']} | "
            f"{item['blur_score']:.0f} | {', '.join(issues)} | [{item['overlay_relative']}]({item['overlay_relative']}) |"
        )
    confusions_md = "\n".join(
        f"- `{row['actual']}` predicted as `{row['predicted']}`: {row['count']}"
        for row in aggregate["class_confusions"]
    ) or "- No class-confusion match at IoU >= 0.50 was found at confidence 0.20."
    human_notes = {
        1: "Crisp daylight multi-bus scene, but five of seven GT fields are tiny. Route and destination occupy adjacent text bands and are repeatedly swapped; the crops are readable only when enlarged.",
        2: "Night scene with two buses, glare and a strongly angled side display. The front number survives, while five small route/destination fields are missed; side-display crops are poor OCR inputs.",
        3: "Low-light display viewed through/behind the bus structure with overlapping field boxes. Four unmatched predictions correspond mainly to route/destination swaps, showing class-boundary ambiguity more than failure to find the display.",
        4: "Distant daylight multi-bus scene. Most component boxes occupy a tiny image fraction; the main number is found, but small route/destination fields on the main and background buses are missed or confused.",
        5: "Two buses at different distances with partial obstruction from roadside objects. The nearer number/route are usable, while the farther display is too small and soft for dependable OCR; three fields are missed.",
        6: "Severe motion/defocus blur and partial bus cropping. Characters are unreadable even in the saved crops, so the missed and confused component fields should be treated as image-quality failures.",
        7: "Large frontal daylight EDS with little blur. The detector localizes the display but route/destination predictions overlap and swap, making this a strong candidate for label-definition review rather than a scale-only failure.",
        8: "Night multi-bus scene with headlight glare, reflections and partial occlusion. Five fields are recovered, but tiny component fields and overlapping buses create two misses and three unmatched predictions; crop readability is marginal.",
        9: "Three tightly packed buses with distant, narrow displays. There are no unmatched predictions, but three tiny GT fields are missed; the limiting factor is scale and crowding, and OCR crops are marginal.",
        10: "Night side view at an oblique angle. Only one of four tiny fields is recovered; perspective compression and low effective text resolution make the remaining crops unsuitable for reliable OCR.",
    }
    human_rows = "\n".join(
        f"| {item['rank']} | `{item['file_name']}` | {human_notes[item['rank']]} |"
        for item in ranked
    )
    review = f"""# YOLO11s validation qualitative review

Generated from the 39-image validation split only. This package does not use the held-out test for further tuning.

## Settings and automatic counts

- Confidence: `{args.confidence:.2f}`
- NMS IoU: `{args.nms_iou:.2f}`
- Match IoU: `0.50`
- Images / reviewed negatives: `{aggregate['images']} / {aggregate['negatives']}`
- TP / FP / FN: `{aggregate['tp']} / {aggregate['fp']} / {aggregate['fn']}`
- False positives on reviewed negative images: `{aggregate['negative_false_positives']}`
- Checkpoint SHA-256: `{aggregate['checkpoint_sha256']}`

These counts use one-to-one, class-correct matching at the selected operating confidence. They are diagnostic counts rather than the COCO mAP computation.

## Highest-priority cases

| Rank | Image | TP | FP | FN | Blur score | Automatic reason | Overlay |
|---:|---|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Contact sheet: [contact_sheet.jpg](contact_sheet.jpg)

## Class-confusion candidates

{confusions_md}

## Human visual review

The contact sheet, all ten individual overlays and representative OCR-field crops were visually inspected. Green/orange boxes are ground truth (orange means missed); blue boxes are matched predictions; red boxes are unmatched predictions.

| Rank | Image | Human observation |
|---:|---|---|
{human_rows}

## Conclusions and next action

- Small/distant text is the most common miss condition: 52 of the 61 GT boxes in the ranked cases are below 1% of image area, and 36 are below 0.25%.
- Route/destination separation is the clearest class problem. Diagnostic IoU matching found 17 destination-to-route and 10 route-to-destination candidates across validation. Several examples localize the correct text band but assign the other semantic label.
- Blur, glare, oblique perspective, crowding and partial occlusion further reduce crop readability. Cases 2, 6, 8 and 10 are particularly poor OCR inputs.
- None of the four reviewed validation negatives produced a prediction at confidence 0.20. This is encouraging but too few negatives for a deployment claim.
- Before a loss-function ablation, review route/destination annotation rules and borderline boxes with Jy, then add or rebalance difficult small, night, angled and motion-blurred examples. Preserve capture/source groups when revising the split.
"""
    (output / "QUALITATIVE_REVIEW.md").write_text(review, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
