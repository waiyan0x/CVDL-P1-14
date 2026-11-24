"""Prepare a separate seven-segment OCR manifest without inventing text labels."""

from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
from PIL import Image, UnidentifiedImageError

from .seven_segment import check_split_leakage, normalize_reading


INPUT_COLUMNS = (
    "sample_id", "crop_path", "display_group_id", "recording_id", "frame_index",
    "field_name", "truth_raw", "label_status", "primary_reviewer",
    "secondary_reviewer", "augmented_from",
)
LABEL_STATUSES = {"readable", "unreadable", "blank", "error"}
SPLITS = ("train", "val", "test")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inventory(csv_path: Path) -> list[dict]:
    """Read crop metadata and validate labels and paths; never infer truth from files."""
    csv_path = csv_path.expanduser().resolve()
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = set(INPUT_COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Inventory is missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)
    if not rows:
        raise ValueError("Inventory has no samples.")
    seen = set()
    for row in rows:
        sample_id = row["sample_id"].strip()
        if not sample_id or sample_id in seen:
            raise ValueError(f"Missing or repeated sample_id: {sample_id!r}")
        seen.add(sample_id)
        for key in ("crop_path", "display_group_id", "recording_id", "field_name"):
            if not row[key].strip():
                raise ValueError(f"{sample_id}: {key} is required.")
        try:
            frame_index = int(row["frame_index"])
        except ValueError as exc:
            raise ValueError(f"{sample_id}: frame_index must be an integer.") from exc
        if frame_index < 0:
            raise ValueError(f"{sample_id}: frame_index must be nonnegative.")
        row["frame_index"] = frame_index
        status = row["label_status"].strip().lower()
        if status not in LABEL_STATUSES:
            raise ValueError(f"{sample_id}: label_status must be one of {sorted(LABEL_STATUSES)}.")
        row["label_status"] = status
        if not row["primary_reviewer"].strip():
            raise ValueError(f"{sample_id}: every label needs a primary reviewer.")
        if status == "readable":
            if not row["truth_raw"].strip():
                raise ValueError(f"{sample_id}: readable label requires visible text.")
            normalize_reading(row["truth_raw"])
        elif row["truth_raw"].strip():
            raise ValueError(f"{sample_id}: {status} labels must not contain inferred text.")
        crop = Path(row["crop_path"]).expanduser()
        if not crop.is_absolute():
            crop = csv_path.parent / crop
        crop = crop.resolve()
        if not crop.is_file():
            raise ValueError(f"{sample_id}: crop file does not exist: {crop}")
        try:
            with Image.open(crop) as image:
                row["input_width"], row["input_height"] = image.size
                row["crop_format"] = image.format
                image.verify()
        except (OSError, UnidentifiedImageError) as exc:
            raise ValueError(f"{sample_id}: crop file is not a decodable image: {crop}") from exc
        row["crop_path"] = str(crop)
        row["crop_sha256"] = _sha256(crop)
        row["reviewed_for_eval"] = (
            bool(row["primary_reviewer"].strip()) and
            bool(row["secondary_reviewer"].strip()) and
            row["primary_reviewer"].strip() != row["secondary_reviewer"].strip()
        )
    for row in rows:
        parent = row["augmented_from"].strip()
        if parent and parent not in seen:
            raise ValueError(f"{row['sample_id']}: augmented_from {parent!r} is missing.")
        if parent == row["sample_id"]:
            raise ValueError(f"{parent}: a crop cannot augment itself.")
    return rows


def assign_splits(rows: list[dict], *, seed: int = 42) -> list[dict]:
    """Assign connected display/recording/augmentation groups to draft splits."""
    parent = {row["sample_id"]: row["sample_id"] for row in rows}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a, b):
        left, right = find(a), find(b)
        parent[max(left, right)] = min(left, right)

    by_display, by_recording = {}, {}
    for row in rows:
        key = row["sample_id"]
        for index, value in ((by_display, row["display_group_id"]),
                             (by_recording, row["recording_id"])):
            if value in index:
                union(key, index[value])
            else:
                index[value] = key
        if row["augmented_from"].strip():
            union(key, row["augmented_from"].strip())
    groups = defaultdict(list)
    for row in rows:
        groups[find(row["sample_id"])].append(row)
    if len(groups) < 3:
        raise ValueError("At least three independent display/recording groups are needed for train, val and test.")
    ordered = sorted(groups.values(), key=lambda group: (-len(group),
        hashlib.sha256(f"{seed}:{min(item['sample_id'] for item in group)}".encode()).hexdigest()))
    targets = {"train": .70 * len(rows), "val": .15 * len(rows), "test": .15 * len(rows)}
    counts = dict.fromkeys(SPLITS, 0)
    for index, group in enumerate(ordered):
        split = SPLITS[index] if index < 3 else max(
            SPLITS, key=lambda name: ((targets[name] - counts[name]) / targets[name],
                                      -SPLITS.index(name)))
        for row in group:
            row["split"] = split
        counts[split] += len(group)
    issues = check_split_leakage(rows)
    if issues:
        raise AssertionError("Group assignment leaked: " + "; ".join(issues))
    return rows


def audit_manifest(rows: list[dict]) -> dict:
    """Return pre-experiment gates; never treat missing review as a passing test."""
    issues = check_split_leakage(rows)
    by_id = {row["sample_id"]: row for row in rows}
    if len(by_id) != len(rows):
        issues.append("sample IDs are not unique")
    for row in rows:
        source_id = row.get("augmented_from", "").strip()
        if source_id and (source_id not in by_id or by_id[source_id]["split"] != row["split"]):
            issues.append(f"augmentation {row['sample_id']} is separated from source {source_id}")
    by_hash = defaultdict(set)
    for row in rows:
        by_hash[row["crop_sha256"]].add(row["split"])
    issues.extend(f"crop hash {digest} appears in {', '.join(sorted(splits))}"
                  for digest, splits in sorted(by_hash.items()) if len(splits) > 1)
    unreviewed = [row["sample_id"] for row in rows
                  if row["split"] in {"val", "test"} and not row["reviewed_for_eval"]]
    if unreviewed:
        issues.append(f"validation/test labels need independent second review: {', '.join(unreviewed)}")
    counts = {split: sum(row["split"] == split for row in rows) for split in SPLITS}
    if any(count == 0 for count in counts.values()):
        issues.append("train, val and test must each have at least one sample")
    features = {}
    for split in SPLITS:
        selected = [row for row in rows if row["split"] == split]
        readable = [row for row in selected if row["label_status"] == "readable"]
        features[split] = {"readable": len(readable),
                           "signed": sum(row["truth_raw"].lstrip().startswith(("+", "-", "−")) for row in readable),
                           "decimal": sum("." in row["truth_raw"] for row in readable),
                           "fields": {name: sum(row["field_name"] == name for row in selected)
                                      for name in sorted({row["field_name"] for row in rows})}}
    return {"sample_count": len(rows), "split_counts": counts, "issues": issues,
            "split_features": features, "ready_for_evaluation": not issues}


def build_manifest(csv_path: Path, *, dataset_id: str, version: str, seed: int = 42) -> dict:
    if not dataset_id.strip() or not version.strip():
        raise ValueError("dataset_id and version are required.")
    rows = assign_splits(load_inventory(csv_path), seed=seed)
    return {"schema_version": 1, "dataset": {"id": dataset_id, "version": version,
            "source_inventory": str(csv_path.expanduser().resolve()), "split_seed": seed,
            "status": "draft"}, "samples": rows, "audit": audit_manifest(rows)}


def write_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
