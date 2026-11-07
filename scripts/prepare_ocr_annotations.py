"""Prepare an unreviewed OCR workspace from an immutable Git handoff snapshot.

Uses the standard library only. Does not run OCR, infer labels or attest review.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import struct
import subprocess
import tarfile
import tempfile


PACKAGE = "evaluation/object_detection/01760a841333/runs/v4-reviewed-01/ocr_handoff"
TEXT_FIELDS = {"front_eds_num", "front_eds_route", "front_eds_destination"}
ORIGINAL_COLUMNS = ["crop", "image", "label", "transcription", "review_status"]
EXTRA_COLUMNS = [
    "crop_source", "image_id", "source_image_sha256", "source_width", "source_height",
    "split", "class_id", "annotation_id", "box_xyxy", "crop_sha256",
    "crop_width", "crop_height", "detector_confidence",
    "matched_gt_annotation_id_at_iou50", "best_same_class_iou", "candidate_gt_crop",
    "correspondence_status", "group_id", "group_review_status", "field_status",
    "legibility", "reviewer", "reviewed_at", "second_reviewer", "second_reviewed_at",
    "exclusion_reason", "notes",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_csv(path, columns, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def prepare(source, output, provenance):
    """Join the original template to crop metadata, failing on inconsistent inputs."""
    manifest_bytes = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    template_bytes = (source / "transcriptions_template.csv").read_bytes()
    reader = csv.DictReader(io.StringIO(template_bytes.decode("utf-8-sig")))
    if reader.fieldnames != ORIGINAL_COLUMNS:
        raise ValueError("Unexpected handoff template columns")
    template = list(reader)
    if len({row["crop"] for row in template}) != len(template):
        raise ValueError("Duplicate template crop IDs")
    # This preparation preserves the unreviewed handoff; it must never erase review.
    if any(row["transcription"] or row["review_status"] != "pending" for row in template):
        raise ValueError("Expected a blank, pending source template; preserve existing review separately")

    metadata = {}
    predictions = []
    images = []
    counts = {}
    crop_hashes = {}
    image_ids = set()
    image_names = set()
    for image in manifest["images"]:
        if image["image_id"] in image_ids or image["image"] in image_names:
            raise ValueError("Duplicate source image identity")
        image_ids.add(image["image_id"])
        image_names.add(image["image"])
        gt_by_id = {item["annotation_id"]: item for item in image["ground_truth"]}
        if len(gt_by_id) != len(image["ground_truth"]):
            raise ValueError("Duplicate annotation ID within source image")
        image_row = {
            "image": image["image"], "image_id": image["image_id"],
            "source_image_sha256": image["image_sha256"], "split": manifest["split"],
            "source_width": image["width"], "source_height": image["height"],
            "annotation_box_count": len(image["ground_truth"]),
            "prediction_box_count": len(image["predictions"]),
            "source_zero_box": str(not image["ground_truth"]).lower(),
            "review_status": "pending", "reviewer": "", "reviewed_at": "",
            "group_id": "", "group_review_status": "pending", "notes": "",
        }
        images.append(image_row)
        for collection, crop_source, count_prefix in (
            ("ground_truth", "annotation", "gt"), ("predictions", "prediction", "pred")
        ):
            for item in image[collection]:
                crop = item["crop"]
                path = PurePosixPath(crop)
                if path.is_absolute() or ".." in path.parts or crop in crop_hashes:
                    raise ValueError(f"Unsafe or duplicate crop path: {crop}")
                data = (source / crop).read_bytes()
                if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
                    raise ValueError(f"Not a PNG crop: {crop}")
                width, height = struct.unpack(">II", data[16:24])
                x1, y1, x2, y2 = item["box_xyxy"]
                if not (0 <= x1 < x2 <= image["width"] and 0 <= y1 < y2 <= image["height"]):
                    raise ValueError(f"Invalid source box: {crop}")
                if (width, height) != (x2 - x1, y2 - y1):
                    raise ValueError(f"Crop size differs from source box: {crop}")
                crop_hashes[crop] = sha256(data)
                key = f"{count_prefix}_{item['label']}"
                counts[key] = counts.get(key, 0) + 1
                if item["label"] not in TEXT_FIELDS:
                    continue
                row = dict.fromkeys(ORIGINAL_COLUMNS + EXTRA_COLUMNS, "")
                row.update(
                    crop=crop, image=image["image"], label=item["label"],
                    review_status="pending", crop_source=crop_source,
                    image_id=image["image_id"], source_image_sha256=image["image_sha256"],
                    source_width=image["width"], source_height=image["height"],
                    split=manifest["split"], class_id=item["class_id"],
                    annotation_id=item.get("annotation_id", ""),
                    box_xyxy=json.dumps(item["box_xyxy"], separators=(",", ":")),
                    crop_sha256=crop_hashes[crop], crop_width=width, crop_height=height,
                    detector_confidence=item.get("confidence", ""),
                    matched_gt_annotation_id_at_iou50=item.get("matched_gt_annotation_id_at_iou50") if item.get("matched_gt_annotation_id_at_iou50") is not None else "",
                    best_same_class_iou=item.get("best_same_class_iou", ""),
                    group_review_status="pending",
                )
                if crop_source == "annotation":
                    metadata[crop] = row
                else:
                    matched = item.get("matched_gt_annotation_id_at_iou50")
                    if matched is not None:
                        candidate = gt_by_id.get(matched)
                        if candidate is None or candidate["label"] != item["label"]:
                            raise ValueError(f"Invalid same-class candidate: {crop}")
                        row["candidate_gt_crop"] = candidate["crop"]
                    row["correspondence_status"] = "pending"
                    predictions.append(row)

    if set(metadata) != {row["crop"] for row in template}:
        raise ValueError("Template and annotation text-crop IDs differ")
    annotations = []
    for original in template:
        row = metadata[original["crop"]].copy()
        if (row["image"], row["label"]) != (original["image"], original["label"]):
            raise ValueError(f"Template provenance mismatch: {original['crop']}")
        row.update(original)  # Retain all five original values and original row order.
        annotations.append(row)
    expected_counts = dict(counts)
    expected_counts["negative_images"] = sum(not image["ground_truth"] for image in manifest["images"])
    expected_counts["predictions_on_negative_images"] = sum(
        len(image["predictions"]) for image in manifest["images"] if not image["ground_truth"]
    )
    if expected_counts != manifest["counts"] or len(images) != manifest["image_count"]:
        raise ValueError("Manifest summary differs from enumerated records")
    actual_crops = {p.relative_to(source).as_posix() for p in source.rglob("*.png")}
    if actual_crops != set(crop_hashes):
        raise ValueError("Manifest and source PNG inventory differ")

    write_csv(output / "annotation_review.csv", ORIGINAL_COLUMNS + EXTRA_COLUMNS, annotations)
    write_csv(output / "prediction_review.csv", ORIGINAL_COLUMNS + EXTRA_COLUMNS, predictions)
    write_csv(output / "image_review.csv", list(images[0]), images)
    source_files = {
        path.relative_to(source).as_posix(): sha256(path.read_bytes())
        for path in sorted(source.rglob("*")) if path.is_file()
    }
    audit = {
        "schema_version": 1, "status": "unreviewed_preparation", "provenance": provenance,
        "source_manifest_sha256": sha256(manifest_bytes),
        "source_template_sha256": sha256(template_bytes), "crop_root": "source",
        "source_image_root": None, "source_images_verified_locally": False,
        "source_image_hashes": "Copied from supplied manifest; originals not included",
        "split": manifest["split"], "image_count": len(images), "counts": expected_counts,
        "annotation_text_rows": len(annotations), "prediction_text_rows": len(predictions),
        "prediction_text_rows_with_iou_candidate": sum(bool(r["candidate_gt_crop"]) for r in predictions),
        "human_reviewed_rows": 0, "scorable_text_rows": 0,
        "crop_checks": "PNG signature/IHDR dimensions, source boxes, IDs, counts and SHA-256; not full pixel decode or human field review",
        "source_files_sha256": source_files,
    }
    (output / "preparation_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# V4 OCR review workspace\n\n"
        "Status: unreviewed preparation; no OCR truth or accuracy is asserted.\n\n"
        "Read repository-root `docs/OCR_ANNOTATION_PACKAGE.md` and "
        "`docs/OCR_TRANSCRIPTION_RULES.md` before review.\n\n"
        "- `annotation_review.csv`: supplied annotation text-crop template plus metadata.\n"
        "- `prediction_review.csv`: independent predicted text-crop review.\n"
        "- `image_review.csv`: all source images, including source zero-box negatives.\n"
        "- `source/`: unchanged Git snapshot; CSV crop paths are relative to this directory.\n"
        "- `preparation_audit.json`: immutable initial provenance, hashes and counts.\n\n"
        "Preserve source files and the initial audit. Save review exports under new names. "
        "Do not infer text from filenames, route references or diagnostic IoU matches.\n",
        encoding="utf-8",
    )
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="origin/bren-object-detection", help="Git ref resolved once to an immutable commit")
    parser.add_argument("--output", type=Path, default=Path("evaluation/ocr_annotations/v4-reviewed-01"))
    args = parser.parse_args()
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    output = args.output.absolute()
    if output.exists():
        parser.error(f"Output already exists; use a new run path: {output}")
    commit = subprocess.check_output(["git", "rev-parse", "--verify", args.ref + "^{commit}"], cwd=repo, text=True).strip()
    archive = subprocess.check_output(["git", "archive", commit, PACKAGE], cwd=repo)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Validate in a sibling temporary directory; publish only a complete workspace.
    with tempfile.TemporaryDirectory(prefix=".ocr-prepare-", dir=output.parent) as temporary:
        staging = Path(temporary) / "workspace"
        source = staging / "source"
        source.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            for member in handle:
                if member.isdir():
                    continue
                path = PurePosixPath(member.name)
                relative = path.relative_to(PACKAGE)
                if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe Git archive member: {member.name}")
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(handle.extractfile(member).read())
        audit = prepare(source, staging, {"git_commit": commit, "git_path": PACKAGE})
        if output.exists():
            raise FileExistsError(output)
        staging.rename(output)
    print(f"Prepared {output}: {audit['annotation_text_rows']} annotation rows, "
          f"{audit['prediction_text_rows']} prediction rows, {audit['image_count']} images; all pending.")


if __name__ == "__main__":
    main()
