"""Compare YOLO11s NMS on validation and rank difficult EDS crop cases."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_preparation.manifests import verify_export


CLASS_NAMES = ("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")
COCO_TO_MODEL = {1: 0, 3: 1, 4: 2, 2: 3}
DATASET = ROOT / "data/training/2026-11-05-roboflow-v4-reviewed"
CHECKPOINT = ROOT / ".runtime/object_detection_benchmark/01760a841333/runs/v4-reviewed-01/yolo11s/weights/best.pt"
OUTPUT = ROOT / "evaluation/object_detection/01760a841333/runs/v4-reviewed-01/validation_review"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection/union if union else 0.0


def diagnostic_match(targets, predictions):
    used = set()
    matches, unmatched_predictions = [], []
    for index in sorted(range(len(predictions)), key=lambda i: -predictions[i]["confidence"]):
        prediction = predictions[index]
        choices = [(i, iou(prediction["box_xyxy"], target["box_xyxy"]))
                   for i, target in enumerate(targets) if i not in used and target["class_id"] == prediction["class_id"]]
        if choices:
            gt_index, overlap = max(choices, key=lambda item: item[1])
            if overlap >= 0.5:
                used.add(gt_index)
                matches.append({"prediction_index": index, "annotation_id": targets[gt_index]["annotation_id"],
                                "iou": round(overlap, 6)})
                continue
        unmatched_predictions.append(index)
    unmatched_gt = [i for i in range(len(targets)) if i not in used]
    confusions = []
    for index in unmatched_predictions:
        prediction = predictions[index]
        choices = [(i, iou(prediction["box_xyxy"], targets[i]["box_xyxy"])) for i in unmatched_gt]
        if choices:
            gt_index, overlap = max(choices, key=lambda item: item[1])
            if overlap >= 0.5 and prediction["class_id"] != targets[gt_index]["class_id"]:
                confusions.append({"actual": targets[gt_index]["label"], "predicted": prediction["label"],
                                   "iou": round(overlap, 6)})
    return matches, unmatched_predictions, unmatched_gt, confusions


def make_overlay(image, item, destination):
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    missed = set(item["unmatched_gt_indices"])
    false = set(item["unmatched_prediction_indices"])
    for index, target in enumerate(item["targets"]):
        color = "orange" if index in missed else "lime"
        draw.rectangle(target["box_xyxy"], outline=color, width=3)
        draw.text(tuple(target["box_xyxy"][:2]), f"GT {target['label']}", fill=color, font=font,
                  stroke_width=2, stroke_fill="black")
    for index, pred in enumerate(item["predictions"]):
        color = "red" if index in false else "cyan"
        draw.rectangle(pred["box_xyxy"], outline=color, width=2)
        draw.text((pred["box_xyxy"][0], pred["box_xyxy"][3]),
                  f"P {pred['label']} {pred['confidence']:.2f}", fill=color, font=font,
                  stroke_width=2, stroke_fill="black")
    canvas.thumbnail((1400, 1100), Image.Resampling.LANCZOS)
    canvas.save(destination, quality=90)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()
    dataset, checkpoint, output = args.dataset.resolve(), args.checkpoint.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output already contains files: {output}")
    if verify_export(dataset) is None or not checkpoint.is_file():
        raise ValueError("Verified dataset and saved checkpoint required")
    coco_path = dataset / "valid/_annotations.coco.json"
    coco = json.loads(coco_path.read_text(encoding="utf-8"))
    annotations = {}
    for ann in coco["annotations"]:
        annotations.setdefault(ann["image_id"], []).append(ann)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".runtime/ultralytics"))
    import torch
    from ultralytics import YOLO
    from torchmetrics.detection.mean_ap import MeanAveragePrecision

    model = YOLO(str(checkpoint))
    if tuple(model.names[i] for i in range(4)) != CLASS_NAMES:
        raise ValueError("Checkpoint class mapping differs")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    images = sorted(coco["images"], key=lambda item: item["file_name"])
    output.mkdir(parents=True, exist_ok=True)
    report = {"dataset_manifest_sha256": sha256(dataset / "preparation_manifest.json"),
              "validation_coco_sha256": sha256(coco_path), "checkpoint_sha256": sha256(checkpoint),
              "split": "valid", "device": device, "image_size": 640, "confidence": 0.5,
              "match_iou": 0.5, "settings": {}}
    for nms in (0.5, 0.7):
        metric = MeanAveragePrecision(box_format="xyxy", class_metrics=True)
        metric50 = MeanAveragePrecision(box_format="xyxy", iou_thresholds=[0.5], class_metrics=True)
        cases = []
        for image_index, info in enumerate(images, 1):
            image_path = (dataset / "valid" / info["file_name"]).resolve()
            if not image_path.is_relative_to((dataset / "valid").resolve()):
                raise ValueError("Invalid image path")
            with Image.open(image_path) as opened:
                image = opened.convert("RGB")
            gt = []
            for ann in annotations.get(info["id"], []):
                x, y, w, h = ann["bbox"]
                class_id = COCO_TO_MODEL[ann["category_id"]]
                gt.append({"annotation_id": ann["id"], "class_id": class_id, "label": CLASS_NAMES[class_id],
                           "box_xyxy": [x, y, x+w, y+h], "area_fraction": w*h/(image.width*image.height)})
            result = model.predict(np.asarray(image)[:, :, ::-1].copy(), imgsz=640, conf=0.001,
                                   iou=nms, classes=list(range(4)), max_det=100, device=device, verbose=False)[0]
            boxes = result.boxes
            all_pred = {"boxes": boxes.xyxy.cpu().float(), "scores": boxes.conf.cpu().float(),
                        "labels": boxes.cls.cpu().long()}
            target = {"boxes": torch.tensor([item["box_xyxy"] for item in gt], dtype=torch.float32).reshape(-1, 4),
                      "labels": torch.tensor([item["class_id"] for item in gt], dtype=torch.int64)}
            metric.update([all_pred], [target])
            metric50.update([all_pred], [target])
            predicted = [{"class_id": int(cls), "label": CLASS_NAMES[int(cls)], "box_xyxy": box,
                          "confidence": round(float(conf), 6)}
                         for box, conf, cls in zip(boxes.xyxy.cpu().tolist(), boxes.conf.cpu().tolist(), boxes.cls.cpu().tolist())
                         if conf >= 0.5]
            matches, fp, fn, confusions = diagnostic_match(gt, predicted)
            tiny = sum(item["area_fraction"] < 0.0025 for item in gt)
            case = {"image": info["file_name"], "image_sha256": sha256(image_path),
                    "negative": not gt, "targets": gt, "predictions": predicted,
                    "matches": matches, "unmatched_prediction_indices": fp, "unmatched_gt_indices": fn,
                    "class_confusions": confusions, "tp": len(matches), "fp": len(fp), "fn": len(fn),
                    "tiny_boxes": tiny, "mean_brightness": round(float(np.asarray(image.convert('L')).mean()), 2),
                    "severity": 10*len(fn)+4*len(fp)+4*len(confusions)+tiny}
            cases.append(case)
            print(f"NMS {nms:.2f}: {image_index}/{len(images)} {info['file_name']} TP {case['tp']} FP {case['fp']} FN {case['fn']}", flush=True)
        m, m50 = metric.compute(), metric50.compute()
        tp, fp, fn = (sum(case[key] for case in cases) for key in ("tp", "fp", "fn"))
        precision = tp/(tp+fp) if tp+fp else 0.0
        recall = tp/(tp+fn) if tp+fn else 0.0
        by_class = {}
        for index, class_id in enumerate(m["classes"].tolist()):
            j = m50["classes"].tolist().index(class_id)
            by_class[CLASS_NAMES[class_id]] = {"map50": float(m50["map_per_class"][j]),
                                               "map50_95": float(m["map_per_class"][index])}
        row = {"images": len(cases), "negatives": sum(case["negative"] for case in cases),
               "map50": float(m50["map_50"]), "map50_95": float(m["map"]), "by_class": by_class,
               "tp": tp, "fp": fp, "fn": fn, "precision_iou50": precision, "recall_iou50": recall,
               "f1_iou50": 2*precision*recall/(precision+recall) if precision+recall else 0.0,
               "negative_false_positives": sum(case["fp"] for case in cases if case["negative"]),
               "cases": cases}
        report["settings"][f"nms_{nms:.2f}"] = row

    reference = report["settings"]["nms_0.70"]
    ranked = sorted(reference["cases"], key=lambda item: (item["severity"], item["fn"], item["fp"]), reverse=True)[:args.top]
    overlays = output / "overlays"
    overlays.mkdir()
    for rank, case in enumerate(ranked, 1):
        with Image.open(dataset / "valid" / case["image"]) as opened:
            image = opened.convert("RGB")
        filename = f"case_{rank:02d}.jpg"
        make_overlay(image, case, overlays / filename)
        case["overlay"] = f"overlays/{filename}"
    successes = [case for case in reference["cases"] if case["targets"] and not case["fp"] and not case["fn"]][:3]
    for rank, case in enumerate(successes, 1):
        with Image.open(dataset / "valid" / case["image"]) as opened:
            image = opened.convert("RGB")
        filename = f"success_{rank:02d}.jpg"
        make_overlay(image, case, overlays / filename)
        case["overlay"] = f"overlays/{filename}"
    report["ranked_case_images"] = [case["image"] for case in ranked]
    report["success_case_images"] = [case["image"] for case in successes]
    (output / "nms_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {k: value[k] for k in ("map50", "map50_95", "tp", "fp", "fn", "f1_iou50", "negative_false_positives")}
                      for key, value in report["settings"].items()}, indent=2))


if __name__ == "__main__":
    main()
