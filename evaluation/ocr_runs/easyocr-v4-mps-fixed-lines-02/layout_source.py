"""Versioned pixel-only line geometry shared across crop recognizers.

Layouts are diagnostic, manually supplied upstream information. They do not
establish deployable automatic line detection or validate text transcriptions.
"""

import json
import math
from pathlib import Path

import cv2
import numpy as np

from .ocr_crop_baseline import sha256


METHOD = "reviewed_full_width_separators_v1"


def line_quads(width, height, separators):
    """Partition a crop with noncrossing straight separators, in pixel-edge coordinates."""
    if not isinstance(separators, list) or len(separators) > 7:
        raise ValueError("Expected at most seven separators")
    previous = [0, 0]
    boundaries = [previous]
    for point in [*separators, [height, height]]:
        if not isinstance(point, list) or len(point) != 2 or any(type(v) is not int for v in point):
            raise ValueError("Separator endpoints must be two integer y coordinates")
        if not all(0 <= value <= height for value in point):
            raise ValueError("Separator escapes crop")
        if min(point[0]-previous[0], point[1]-previous[1]) < 2:
            raise ValueError("Crossing, unordered or thinner-than-two-pixel line region")
        boundaries.append(point)
        previous = point
    return [[[0, upper[0]], [width, upper[1]], [width, lower[1]], [0, lower[0]]]
            for upper, lower in zip(boundaries, boundaries[1:])]


def validate_entry(entry, record):
    for key in ("review_id", "crop_id", "crop_sha256", "input_width", "input_height"):
        if entry.get(key) != record.get(key):
            raise ValueError(f"Layout/source {key} mismatch: {record['review_id']}")
    if entry.get("review_status") not in {"accepted", "unresolved"}:
        raise ValueError("Layout must explicitly be accepted or unresolved")
    if not entry.get("reviewer") or not entry.get("reviewed_at") or entry.get("reviewer_type") != "AI":
        raise ValueError("This layout version requires explicit AI reviewer attribution/date")
    if entry["review_status"] == "unresolved":
        if entry.get("line_quads") or entry.get("separators") or not entry.get("reason"):
            raise ValueError("Unresolved layout needs a reason and no recognition regions")
    elif entry.get("line_quads") != line_quads(record["input_width"], record["input_height"], entry["separators"]):
        raise ValueError("Stored line quadrilaterals do not match reviewed separators")
    return entry


def load_layout(path, records):
    path = Path(path)
    expected_hash = path.with_suffix(".sha256").read_text().split()[0]
    if sha256(path) != expected_hash:
        raise ValueError("Frozen line-layout hash mismatch")
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("method") != METHOD or not manifest.get("frozen"):
        raise ValueError("Unsupported or unfrozen layout manifest")
    entries = manifest.get("entries", [])
    by_id = {entry["review_id"]: entry for entry in entries}
    if len(entries) != len(by_id) or set(by_id) != {r["review_id"] for r in records}:
        raise ValueError("Layout has duplicate, missing or unexpected crop IDs")
    for record in records:
        validate_entry(by_id[record["review_id"]], record)
    return manifest, by_id


def extract_region(image, quad):
    """Slice horizontal bands exactly; rectify sloping bands with logged linear interpolation."""
    width = image.shape[1]
    top_left, top_right, bottom_right, bottom_left = quad
    if top_left[1] == top_right[1] and bottom_left[1] == bottom_right[1]:
        return image[top_left[1]:bottom_left[1], :].copy()
    output_height = math.ceil(max(bottom_left[1]-top_left[1], bottom_right[1]-top_right[1]))
    target = np.float32([[0, 0], [width, 0], [width, output_height], [0, output_height]])
    matrix = cv2.getPerspectiveTransform(np.float32(quad), target)
    return cv2.warpPerspective(image, matrix, (width, output_height),
                               flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
