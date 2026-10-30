"""Validate reviewed transcriptions and exclude known image leakage by default."""
import json
import math
import re
from datetime import datetime
from pathlib import Path

from .provenance import file_hash, image_hashes


def _required_strings(value: dict, fields: tuple, label: str) -> None:
    if not isinstance(value, dict) or any(not isinstance(value.get(key), str) or not value[key].strip() for key in fields):
        raise ValueError(f"{label} requires {', '.join(fields)}.")


def load_manifest(path: Path) -> dict:
    path = path.resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported manifest schema_version; expected 1.")
    _required_strings(manifest.get("dataset"), ("id", "version", "split"), "Dataset identity")
    review = manifest.get("review", {})
    if review.get("reviewed") is not True:
        raise ValueError("A human-reviewed transcription manifest is required; review.reviewed must be true.")
    _required_strings(review, ("reviewer", "reviewed_at"), "Human review")
    try:
        datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Human review date must be an ISO date or timestamp.") from exc
    if manifest["dataset"]["split"] not in {"val", "test", "held_out"}:
        raise ValueError("Evaluation split must be val, test, or held_out, never train.")
    images = manifest.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("The manifest must contain at least one reviewed image.")
    seen = set()
    for image in images:
        _required_strings(image, ("id", "path", "sha256"), "Image identity")
        if image["id"] in seen:
            raise ValueError("Each manifest image ID must be unique.")
        seen.add(image["id"])
        image_path = (path.parent / image["path"]).resolve()
        if not image_path.is_file():
            raise ValueError(f"Image does not exist: {image['path']}")
        if not re.fullmatch(r"[0-9a-f]{64}", image["sha256"]) or file_hash(image_path) != image["sha256"]:
            raise ValueError(f"Image hash mismatch: {image['id']}")
        image["resolved_path"] = image_path
        displays = image.get("displays")
        if not isinstance(displays, list):
            raise ValueError("Each image requires displays; use an empty list for a reviewed negative image.")
        display_ids = set()
        for display in displays:
            _required_strings(display, ("id",), "Display identity")
            if display["id"] in display_ids:
                raise ValueError("Display IDs must be unique within an image.")
            display_ids.add(display["id"])
            box = display.get("box")
            if not isinstance(box, list) or len(box) != 4 or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in box):
                raise ValueError("Display box requires four finite nonnegative pixel coordinates.")
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError("Display box must have positive width and height.")
            for field in ("bus_number", "destination"):
                if field not in display or (display[field] is not None and not isinstance(display[field], str)):
                    raise ValueError(f"Each display requires {field}: reviewed text or null when unscored.")
            if display["bus_number"] is None and display["destination"] is None:
                raise ValueError("A display must have at least one reviewed text field.")
    manifest["manifest_path"] = str(path)
    manifest["manifest_sha256"] = file_hash(path)
    return manifest


def select_images(manifest: dict, root: Path, include_overlap: bool = False) -> tuple[list, list]:
    training_hashes = image_hashes(root, "train")
    selected, excluded, seen = [], [], set()
    for image in manifest["images"]:
        reason = None
        if image["sha256"] in seen:
            reason = "duplicate_within_manifest"
        elif image["sha256"] in training_hashes and not include_overlap:
            reason = "training_overlap"
        seen.add(image["sha256"])
        if reason:
            excluded.append({"id": image["id"], "sha256": image["sha256"], "reason": reason,
                             "training_files": training_hashes.get(image["sha256"], [])})
        else:
            selected.append(image)
    return selected, excluded
