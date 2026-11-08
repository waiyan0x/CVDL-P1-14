"""Create a human-review packet for EDS classes, negatives and split grouping."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "training" / "2026-10-30-torchvision"
DEFAULT_OUTPUT = (
    ROOT / "evaluation" / "object_detection" / "bf938f526d2c" / "runs"
    / "baseline-01" / "data_review"
)
CLASS_NAMES = {
    1: "front_eds",
    2: "front_eds_destination",
    3: "front_eds_num",
    4: "front_eds_route",
}
COLORS = {
    1: (30, 220, 80),
    2: (235, 70, 220),
    3: (40, 210, 235),
    4: (245, 190, 35),
}


def box_xyxy(annotation: dict) -> list[float]:
    x, y, width, height = annotation["bbox"]
    return [float(x), float(y), float(x + width), float(y + height)]


def intersection(first: list[float], second: list[float]) -> float:
    width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    return width * height


def area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def iou(first: list[float], second: list[float]) -> float:
    overlap = intersection(first, second)
    union = area(first) + area(second) - overlap
    return overlap / union if union else 0.0


def containment(inner: list[float], outer: list[float]) -> float:
    inner_area = area(inner)
    return intersection(inner, outer) / inner_area if inner_area else 0.0


def source_stem(file_name: str) -> str:
    return re.sub(r"_jpg\.rf\.[0-9a-f]+$", "", Path(file_name).stem, flags=re.I)


def capture_group(file_name: str) -> str | None:
    """Infer only high-confidence timestamp-session groups from filenames."""
    stem = source_stem(file_name)
    patterns = (
        (r"^(Screenshot_\d{4}-\d{2}-\d{2}-\d{2}-\d{2})-\d{2}-\d+_", "screenshot-minute"),
        (r"^(IMAGE_\d{4}-\d{2}-\d{2}_\d{2}_\d{2})_\d{2}$", "image-minute"),
        (r"^(IMG\d{12})\d{2}$", "img-minute"),
        (r"^(photo_\d{4}-\d{2}-\d{2}_\d{2}-\d{2})-\d{2}$", "photo-minute"),
    )
    for pattern, prefix in patterns:
        match = re.match(pattern, stem, flags=re.I)
        if match:
            return f"{prefix}:{match.group(1).lower()}"
    return None


def draw_overlay(record: dict, destination: Path) -> None:
    with Image.open(record["path"]) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    line_width = max(2, round(max(image.size) / 500))
    for annotation in record["annotations"]:
        category = annotation["category_id"]
        box = box_xyxy(annotation)
        color = COLORS[category]
        draw.rectangle(box, outline=color, width=line_width)
        label = CLASS_NAMES[category]
        text_box = draw.textbbox((box[0], box[1]), label, font=font)
        draw.rectangle(text_box, fill=color)
        draw.text((box[0], box[1]), label, fill=(0, 0, 0), font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, quality=90)


def make_sheet(items: list[dict], destination: Path, title_key: str) -> None:
    if not items:
        return
    thumbs = []
    for item in items:
        with Image.open(item["overlay"]) as opened:
            image = opened.convert("RGB")
        image.thumbnail((520, 330))
        canvas = Image.new("RGB", (540, 380), "white")
        canvas.paste(image, ((540 - image.width) // 2, 35))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 8), item[title_key][:82], fill="black")
        draw.text((8, 355), "; ".join(item.get("reasons", []))[:88], fill="black")
        thumbs.append(canvas)
    rows = (len(thumbs) + 1) // 2
    sheet = Image.new("RGB", (1080, rows * 380), "white")
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % 2) * 540, (index // 2) * 380))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=90)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-candidates", type=int, default=20)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Review output already exists: {output}")
    output.mkdir(parents=True)

    manifest = json.loads((dataset / "augmentation_manifest.json").read_text(encoding="utf-8"))
    provenance = {row["output"]: row for row in manifest["training_provenance"]}
    records = []
    category_counts: dict[str, Counter] = {}
    split_counts = {}
    for split in ("train", "valid", "test"):
        payload = json.loads((dataset / split / "_annotations.coco.json").read_text(encoding="utf-8"))
        by_image = defaultdict(list)
        for annotation in payload["annotations"]:
            if annotation["category_id"] in CLASS_NAMES:
                by_image[annotation["image_id"]].append(annotation)
        counts = Counter()
        original_images = 0
        negatives = 0
        for image_row in payload["images"]:
            file_name = image_row["file_name"]
            original = split != "train" or provenance[file_name]["variant"] == 0
            if not original:
                continue
            original_images += 1
            annotations = by_image[image_row["id"]]
            if not annotations:
                negatives += 1
            counts.update(CLASS_NAMES[item["category_id"]] for item in annotations)
            records.append({
                "split": split,
                "file_name": file_name,
                "path": str(dataset / split / file_name),
                "width": image_row["width"],
                "height": image_row["height"],
                "annotations": annotations,
                "negative": not annotations,
                "capture_group": capture_group(file_name),
            })
        category_counts[split] = counts
        split_counts[split] = {"original_images": original_images, "negative_images": negatives, "boxes": sum(counts.values())}

    issue_records = []
    for record in records:
        if record["negative"]:
            continue
        annotations = record["annotations"]
        panels = [item for item in annotations if item["category_id"] == 1]
        contents = [item for item in annotations if item["category_id"] != 1]
        reasons = []
        details = []
        for content in contents:
            ratio = max((containment(box_xyxy(content), box_xyxy(panel)) for panel in panels), default=0.0)
            if ratio < 0.90:
                reasons.append("content outside panel")
                details.append({"type": "content_outside_panel", "class": CLASS_NAMES[content["category_id"]], "containment": ratio})
        for panel in panels:
            associated = [item for item in contents if containment(box_xyxy(item), box_xyxy(panel)) >= 0.50]
            if not associated:
                reasons.append("panel without content")
                details.append({"type": "panel_without_content"})
        routes = [item for item in annotations if item["category_id"] == 4]
        destinations = [item for item in annotations if item["category_id"] == 2]
        for route in routes:
            for destination in destinations:
                overlap = iou(box_xyxy(route), box_xyxy(destination))
                if overlap >= 0.50:
                    reasons.append("route/destination overlap")
                    details.append({"type": "route_destination_overlap", "iou": overlap})
        for category in CLASS_NAMES:
            same = [item for item in annotations if item["category_id"] == category]
            for left in range(len(same)):
                for right in range(left + 1, len(same)):
                    overlap = iou(box_xyxy(same[left]), box_xyxy(same[right]))
                    if overlap >= 0.85:
                        reasons.append("possible duplicate box")
                        details.append({"type": "possible_duplicate", "class": CLASS_NAMES[category], "iou": overlap})
        if reasons:
            unique_reasons = list(dict.fromkeys(reasons))
            severity = 4 * sum(item["type"] == "content_outside_panel" for item in details)
            severity += 3 * sum(item["type"] == "route_destination_overlap" for item in details)
            severity += 2 * sum(item["type"] == "possible_duplicate" for item in details)
            severity += sum(item["type"] == "panel_without_content" for item in details)
            issue_records.append({**record, "reasons": unique_reasons, "details": details, "severity": severity})

    issue_records.sort(key=lambda item: (item["severity"], len(item["details"])), reverse=True)
    review_candidates = issue_records[: args.max_candidates]
    overlay_dir = output / "candidate_overlays"
    for index, record in enumerate(review_candidates, 1):
        overlay = overlay_dir / f"case_{index:02d}.jpg"
        draw_overlay(record, overlay)
        record["overlay"] = str(overlay)
        record["overlay_relative"] = str(overlay.relative_to(output)).replace("\\", "/")
    make_sheet(review_candidates, output / "semantic_candidates.jpg", "file_name")

    negatives = [item for item in records if item["negative"]]
    negative_samples = []
    for record in negatives:
        # The contact sheet is sufficient evidence; do not duplicate all source images.
        negative_samples.append({**record, "overlay": record["path"], "reasons": [record["split"]]})
    make_sheet(negative_samples, output / "negative_contact_sheet.jpg", "file_name")

    grouped = defaultdict(list)
    for record in records:
        if record["capture_group"]:
            grouped[record["capture_group"]].append(record)
    cross_split_groups = []
    for group, members in sorted(grouped.items()):
        splits = sorted({item["split"] for item in members})
        if len(splits) > 1:
            cross_split_groups.append({
                "group": group,
                "splits": splits,
                "files": [{"split": item["split"], "file_name": item["file_name"]} for item in members],
            })

    issue_type_counts = Counter(detail["type"] for item in issue_records for detail in item["details"])
    report = {
        "dataset": str(dataset),
        "scope": "original train images plus unaugmented validation/test",
        "split_counts": split_counts,
        "class_counts": {split: dict(counts) for split, counts in category_counts.items()},
        "semantic_candidate_images": len(issue_records),
        "semantic_candidate_events": dict(issue_type_counts),
        "review_candidates": [
            {key: value for key, value in item.items() if key not in {"annotations", "path", "overlay"}}
            for item in review_candidates
        ],
        "negative_images": [{"split": item["split"], "file_name": item["file_name"]} for item in negatives],
        "timestamp_groups_crossing_splits": cross_split_groups,
        "limitations": [
            "Structural heuristics are review candidates, not proof of annotation error.",
            "Filename timestamp grouping is evidence of possible shared capture sessions, not verified provenance.",
            "The dataset contains no source-permission register or platform Null history.",
            "Human confirmation by the annotation owners is still required before labels or splits are changed.",
        ],
    }
    (output / "semantic_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    class_rows = "\n".join(
        f"| {split} | {split_counts[split]['original_images']} | {split_counts[split]['negative_images']} | "
        f"{category_counts[split]['front_eds']} | {category_counts[split]['front_eds_num']} | "
        f"{category_counts[split]['front_eds_route']} | {category_counts[split]['front_eds_destination']} |"
        for split in ("train", "valid", "test")
    )
    candidate_rows = "\n".join(
        f"| {index} | {item['split']} | `{item['file_name']}` | {', '.join(item['reasons'])} | "
        f"[overlay]({item['overlay_relative']}) | Pending Jy/Brendan decision |"
        for index, item in enumerate(review_candidates, 1)
    ) or "| - | - | - | No structural candidates | - | - |"
    group_rows = "\n".join(
        f"| `{item['group']}` | {', '.join(item['splits'])} | {len(item['files'])} | Pending provenance confirmation |"
        for item in cross_split_groups
    ) or "| - | - | 0 | No timestamp-derived cross-split group found |"
    review = f"""# Task 3 — class, negative and split review

This packet audits the exact detector dataset used for the benchmark. It covers the 137 original training images plus 39 validation and 20 test images. The 274 training augmentations inherit their source annotations and are not counted as independent human-label decisions.

## Locked label contract

| Training index | COCO ID | Class | Decision rule |
|---:|---:|---|---|
| 0 | 1 | `front_eds` | Complete visible front- or side-facing EDS panel; rear displays excluded. |
| 1 | 3 | `front_eds_num` | Whole service-number group, including letter suffixes. |
| 2 | 4 | `front_eds_route` | Smaller/thinner intermediate road, stop or “via” text; meaning and typography, not position. |
| 3 | 2 | `front_eds_destination` | Larger/bolder final destination/terminal text and associated arrow/symbol. |

The unused COCO parent category `0: front-eds` has no boxes and is not a fifth foreground class. A true negative contains no eligible front or side EDS and therefore has zero COCO annotations—never a background-class box.

## Original-image inventory

| Split | Images | Zero-box | Panel | Number | Route | Destination |
|---|---:|---:|---:|---:|---:|---:|
{class_rows}

The full manifest-backed export also passes the existing automated readiness audit: 411/39/20 images, 1,644/154/83 boxes, and no exact/dHash cross-split match at the configured threshold. That does not prove semantic correctness or capture-session independence.

## Semantic candidates for joint review

These are heuristic flags, not automatic corrections. Inspect the image and annotation guide before accepting, relabeling or rejecting anything.

| # | Split | Image | Reason | Evidence | Human decision |
|---:|---|---|---|---|---|
{candidate_rows}

Contact sheet: [semantic_candidates.jpg](semantic_candidates.jpg)

## Negative review

There are {len(negatives)} original zero-box images: {split_counts['train']['negative_images']} train, {split_counts['valid']['negative_images']} validation and {split_counts['test']['negative_images']} test. Review every image on [negative_contact_sheet.jpg](negative_contact_sheet.jpg) against this rule: rear-only EDS, unrelated signs and scenes without an eligible visible front/side EDS stay negative; any visible eligible front/side panel requires boxes. The COCO export cannot prove these were explicitly marked Null in the annotation platform.

## Capture/source split isolation

The following timestamp-derived filename groups span more than one split. This is a conservative provenance warning: the filenames suggest the same minute/session, but only the original source/recording records can confirm whether they are frames from one capture.

| Inferred group | Splits | Images | Decision |
|---|---|---:|---|
{group_rows}

The current repository has hashes and augmentation lineage but no authoritative capture/recording IDs or source-permission register. Therefore Task 3 cannot honestly certify split isolation or usage permission yet.

## Approval checklist for Brendan and Jy

- [ ] Confirm all four class definitions and the COCO-to-training mapping above.
- [ ] Decide every semantic candidate row; record keep/relabel/add/remove and reviewer initials.
- [ ] Confirm every original zero-box image is a valid negative and was explicitly accepted as Null, if platform history is available.
- [ ] Confirm whether each inferred cross-split timestamp group belongs to one recording/capture. If yes, rebuild a grouped split before the next benchmark; do not silently move only selected frames.
- [ ] Add source owner/origin and usage permission for each capture group or source collection.
- [ ] If annotations or splits change, publish a new versioned dataset/manifest and rerun all three models; preserve the current baseline as historical evidence.

No dataset labels or split assignments were changed by this audit.
"""
    (output / "REVIEW.md").write_text(review, encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "split_counts": split_counts,
        "semantic_candidate_images": len(issue_records),
        "semantic_candidate_events": dict(issue_type_counts),
        "cross_split_timestamp_groups": len(cross_split_groups),
    }, indent=2))


if __name__ == "__main__":
    main()
