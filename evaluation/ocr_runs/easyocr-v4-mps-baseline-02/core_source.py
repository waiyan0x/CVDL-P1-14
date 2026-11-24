"""Recognition-only crop inference and deterministic, label-independent line regions."""

from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
from PIL import Image


FIELDS = ("front_eds_num", "front_eds_route", "front_eds_destination")
SEGMENTATION = {
    "id": "row_projection_v2",
    "foreground": "Otsu/border polarity; for bright text, use warm/green chromatic support when >=1% of pixels and >=12% of Otsu support",
    "chromatic_support": "max(R,G)-B>12, max(R,G,B)-min(R,G,B)>20, grayscale>max(20,0.5*Otsu)",
    "active_row": "foreground count >= max(1, 0.02*width, 0.20*peak row count)",
    "close_vertical_gaps": "base max(1,floor(height*0.025)); with >=3 bands, bridge up to twice the median of the smaller half of gaps, capped at floor(height/5)",
    "minimum_band_height": "max(2, floor(crop_height * 0.06)) pixels",
    "regions": "full-width partitions at midpoints between retained bands; preserve all rows",
    "max_lines": 8,
    "layout_verification": "All regions are heuristic and unverified; inspect saved overlays",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_crops(workspace):
    """Select identity/geometry only. Never use submitted transcription or legibility."""
    root = (workspace / "source").resolve()
    records = []
    for kind, prefix, count in (("annotation", "A", 157), ("prediction", "P", 114)):
        path = workspace / "human_review" / f"{kind}_submission.template.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != count or {r["review_id"] for r in rows} != {f"{prefix}{n:03d}" for n in range(1, count+1)}:
            raise ValueError(f"Unexpected IDs or row count: {path}")
        for row in rows:
            crop = (root / row["crop"]).resolve()
            if not crop.is_relative_to(root) or not crop.is_file():
                raise ValueError(f"Invalid crop path: {row['crop']}")
            if row["label"] not in FIELDS or row["split"] != "valid":
                raise ValueError(f"Unexpected field/split: {row['review_id']}")
            if sha256(crop) != row["crop_sha256"]:
                raise ValueError(f"Crop hash mismatch: {row['review_id']}")
            records.append({
                "review_id": row["review_id"], "crop_set": kind, "field": row["label"],
                "crop_id": row["crop"], "crop_path": str(crop), "crop_sha256": row["crop_sha256"],
                "source_image": row["image"], "source_image_sha256": row["source_image_sha256"],
                "input_width": int(row["crop_width"]), "input_height": int(row["crop_height"]),
            })
    if len({r["crop_id"] for r in records}) != len(records):
        raise ValueError("Duplicate crop IDs")
    return records


def _runs(active):
    starts, ends = [], []
    previous = False
    for index, current in enumerate(list(active) + [False]):
        if current and not previous:
            starts.append(index)
        if previous and not current:
            ends.append(index)
        previous = bool(current)
    return list(zip(starts, ends))


def segment_lines(rgb):
    """Return full-width line partitions plus uncertainty; no OCR or labels involved."""
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 2:
        raise ValueError("Expected an RGB crop of at least 2x2 pixels")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    if int(gray.max()) == int(gray.min()):
        return gray, [], {"status": "no_contrast", "needs_review": True}
    threshold, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    bright = float(np.median(border)) <= threshold
    foreground = gray > threshold if bright else gray <= threshold
    foreground_mode = "grayscale"
    if bright:
        channels = rgb.astype(np.int16)
        chromatic = ((np.maximum(channels[:, :, 0], channels[:, :, 1])-channels[:, :, 2] > 12)
                     & (channels.max(axis=2)-channels.min(axis=2) > 20)
                     & (gray > max(20, threshold*0.5)))
        if chromatic.sum() >= max(gray.size*0.01, foreground.sum()*0.12):
            foreground = chromatic
            foreground_mode = "chromatic_led_support"
    projection = foreground.sum(axis=1)
    active = projection >= max(1, width*0.02, 0.20*int(projection.max()))
    close_gap = max(1, math.floor(height * 0.025))
    bands = _runs(active)
    if len(bands) >= 3:
        gaps = sorted(right[0]-left[1] for left, right in zip(bands, bands[1:]))
        lower_half = gaps[:max(1, (len(gaps)+1)//2)]
        texture_gap = int(np.median(lower_half)*2)
        close_gap = max(close_gap, min(texture_gap, max(1, height//5)))
    for (_, end), (start, _) in zip(bands, bands[1:]):
        if start - end <= close_gap:
            active[end:start] = True
    minimum_height = max(2, math.floor(height * 0.06))
    bands = [(a, b) for a, b in _runs(active) if b-a >= minimum_height]
    info = {"status": "split_candidate" if len(bands) > 1 else "single_band_unverified",
            "needs_review": True, "threshold": float(threshold), "polarity": "bright" if bright else "dark",
            "foreground_mode": foreground_mode, "bridged_gap_pixels": close_gap,
            "foreground_bands": [list(band) for band in bands]}
    if not bands or len(bands) > SEGMENTATION["max_lines"]:
        info["status"] = "no_supported_bands" if not bands else "fragmented_ambiguous"
        return gray, [], info
    boundaries = [0] + [(left[1] + right[0]) // 2 for left, right in zip(bands, bands[1:])] + [height]
    return gray, [[0, top, width, bottom] for top, bottom in zip(boundaries, boundaries[1:])], info


def recognize_crop(record, reader, synchronize):
    """Measure one crop. Failed crops/lines retain IDs and partial outputs."""
    result = {key: value for key, value in record.items() if key != "crop_path"}
    result.update(status="error", raw_text="", ocr_confidence=None, error=None,
                  segmentation=None, line_regions=[], line_outputs=[], preprocessing_ms=None, recognition_ms=0.0,
                  crop_total_ms=None, line_count=0)
    synchronize()
    start = perf_counter()
    try:
        data = Path(record["crop_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["crop_sha256"]:
            raise ValueError("Crop changed after preflight")
        with Image.open(io.BytesIO(data)) as image:
            if image.size != (record["input_width"], record["input_height"]):
                raise ValueError("Crop dimensions differ from manifest")
            rgb = np.asarray(image.convert("RGB"))
        gray, regions, info = segment_lines(rgb)
        result["preprocessing_ms"] = (perf_counter()-start)*1000
        result["segmentation"] = info
        result["line_regions"] = regions
        result["line_count"] = len(regions)
        if not regions:
            raise ValueError(f"Line segmentation unresolved: {info['status']}; full-crop recognition was not substituted")
        for index, box in enumerate(regions):
            x1, y1, x2, y2 = box
            line = gray[y1:y2, x1:x2].copy()
            synchronize()
            line_start = perf_counter()
            try:
                output = reader.recognize(
                    line, horizontal_list=[[0, line.shape[1], 0, line.shape[0]]], free_list=[],
                    detail=1, decoder="greedy", batch_size=1, workers=0, allowlist=None,
                    blocklist=None, paragraph=False, contrast_ths=0.0, reformat=False,
                )
                synchronize()
            finally:
                duration = (perf_counter()-line_start)*1000
                result["recognition_ms"] += duration
            items = []
            for entry in output:
                score = float(entry[2])
                items.append({"text": entry[1], "confidence": score if math.isfinite(score) else None})
            result["line_outputs"].append({"index": index, "box_xyxy": box, "recognition_ms": duration,
                                            "items": items, "raw_text": "\n".join(item["text"] for item in items)})
        result["raw_text"] = "\n".join(line["raw_text"] for line in result["line_outputs"])
        items = [item for line in result["line_outputs"] for item in line["items"] if item["text"]]
        chars = sum(len(item["text"]) for item in items)
        if chars and all(item["confidence"] is not None for item in items):
            result["ocr_confidence"] = sum(len(item["text"])*item["confidence"] for item in items)/chars
        result["status"] = "success"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["raw_text"] = "\n".join(line["raw_text"] for line in result["line_outputs"])
        # Partial output from a failed multiline crop is not a successful prediction.
        result["ocr_confidence"] = None
    finally:
        result["crop_total_ms"] = (perf_counter()-start)*1000
    return result


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered)-1)*fraction
    low, high = math.floor(point), math.ceil(point)
    return ordered[low] + (ordered[high]-ordered[low])*(point-low)


def summarize(results):
    summary = []
    for kind in ("annotation", "prediction"):
        for field in (*FIELDS, "all"):
            rows = [r for r in results if r["crop_set"] == kind and (field == "all" or r["field"] == field)]
            successful = [r for r in rows if r["status"] == "success"]
            stats = {"crop_set": kind, "field": field, "attempted": len(rows),
                     "completed": len(successful), "errors": len(rows)-len(successful),
                     "empty_outputs": sum(not r["raw_text"].strip() for r in successful),
                     "multiline_candidates": sum(r["line_count"] > 1 for r in rows),
                     "segmentation_status_counts": dict(Counter((r["segmentation"] or {}).get("status", "not_reached") for r in rows)),
                     "timing_population": "successful crops only; error counts and individual error times retained"}
            for metric in ("preprocessing_ms", "recognition_ms", "crop_total_ms"):
                values = [r[metric] for r in successful]
                stats[f"{metric}_median"] = percentile(values, 0.5)
                stats[f"{metric}_p95"] = percentile(values, 0.95)
            summary.append(stats)
    return summary
