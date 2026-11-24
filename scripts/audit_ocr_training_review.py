"""Validate the AI review package without declaring labels training-ready."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import unicodedata
import zipfile

from PIL import Image


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def audit(workspace):
    intake = json.loads((workspace / "intake_audit.json").read_text())
    manifest = json.loads((workspace / "source_manifest.json").read_text())
    crop_root = Path(intake["crop_root"])
    with (workspace / "transcriptions.review.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    with (workspace / "source_transcriptions_template.csv").open(newline="", encoding="utf-8-sig") as handle:
        original = list(csv.DictReader(handle))
    assert len(rows) == len(original) == 1917
    assert len({r["review_id"] for r in rows}) == len(rows)
    assert len({r["crop"] for r in rows}) == len(rows)
    assert len({r["annotation_id"] for r in rows}) == len(rows)
    assert all(not r["transcription"] and r["review_status"] == "pending" for r in original)
    metadata = {
        g["crop"]: (image, g)
        for image in manifest["images"]
        for g in image["ground_truth"]
    }
    validation = json.loads(Path(
        "evaluation/ocr_annotations/v4-reviewed-01/source/manifest.json"
    ).read_text())
    validation_hashes = {im["image_sha256"] for im in validation["images"]}
    state_counts = Counter()
    for row, source in zip(rows, original, strict=True):
        for key in ("crop", "image", "label", "annotation_id", "source_name"):
            assert row[key] == source[key], (row["review_id"], key)
        image, geometry = metadata[row["crop"]]
        assert row["source_image_sha256"] == image["image_sha256"]
        assert row["source_image_sha256"] not in validation_hashes
        assert json.loads(row["box_xyxy"]) == geometry["box_xyxy"]
        assert int(row["class_id"]) == geometry["class_id"]
        path = crop_root / row["crop"]
        assert path.resolve().is_relative_to(crop_root.resolve())
        assert sha256(path) == row["crop_sha256"]
        with Image.open(path) as crop:
            crop.load()
            assert crop.size == (int(row["crop_width"]), int(row["crop_height"]))
        text = row["transcription"]
        assert text == unicodedata.normalize("NFC", text)
        assert "\\n" not in text
        assert all(line == line.strip() and "  " not in line for line in text.splitlines())
        if row["legibility"] == "full":
            assert text and "[UNK]" not in text
        elif row["legibility"] == "partial":
            assert "[UNK]" in text and text != "[UNK]"
        else:
            assert row["legibility"] == "illegible" and text == "[UNK]"
        assert row["reviewer"] == "Codex" and row["reviewer_type"] == "AI"
        assert row["reviewed_at"].startswith("2026-11-09T")
        assert not row["second_reviewer"] and not row["second_reviewed_at"]
        assert row["split"] == "train"
        assert row["group_review_status"] == "needs_resolution"
        assert row["human_verification_status"] == "pending"
        assert row["training_ready"] == "false"
        state_counts[(row["label"], row["legibility"])] += 1
    source_files = {}
    for name, expected in intake["source_archives"].items():
        path = Path("/Users/tanyilin/Downloads") / name
        assert sha256(path) == expected
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            for filename in ("manifest.json", "transcriptions_template.csv", "README.md"):
                assert archive.read(filename) == (workspace / ("source_" + filename)).read_bytes()
        source_files[name] = expected
    sources = list(csv.DictReader((workspace / "source_review.csv").open(newline="")))
    assert len(sources) == 735
    candidates = list(csv.DictReader((workspace / "full_text.ai-candidates.csv").open(newline="")))
    for row in candidates:
        assert row["legibility"] == "full" and row["training_ready"] == "false"
        assert row["training_disposition"] == "needs_human_verification"
        assert row["field_review_status"] != "needs_resolution"
    results = {
        "status": "structurally_valid_ai_review_not_training_ready",
        "review_date": "2026-11-09",
        "reviewer": "Codex",
        "reviewer_type": "AI",
        "text_crops": len(rows),
        "training_source_images": len(sources),
        "named_training_families": len({s["source_name"] for s in sources}),
        "training_groups": len({s["group_id"] for s in sources}),
        "legibility_counts": dict(Counter(r["legibility"] for r in rows)),
        "field_counts": {
            label: {state: state_counts[label, state] for state in ("full", "partial", "illegible")}
            for label in sorted({r["label"] for r in rows})
        },
        "review_status_counts": dict(Counter(r["review_status"] for r in rows)),
        "quarantined_source_images": sum(s["holdout_link"] == "True" for s in sources),
        "quarantined_groups": len({s["group_id"] for s in sources if s["holdout_link"] == "True"}),
        "quarantined_text_rows": sum(r["training_disposition"] == "quarantined_legacy_holdout_candidate" for r in rows),
        "human_verification_candidates": len(candidates),
        "training_ready_rows": 0,
        "current_validation_exact_source_hash_overlap": 0,
        "source_archives_sha256": source_files,
        "artifact_sha256": {
            name: sha256(workspace / name)
            for name in ("transcriptions.review.csv", "human_review_queue.csv",
                         "full_text.ai-candidates.csv", "source_review.csv",
                         "source_audit.json", "source_groups.json")
        },
        "limits": [
            "Counts are annotation coverage, not OCR accuracy.",
            "AI reinspection is not independent human review.",
            "Historical source-name links do not establish new v4 split leakage.",
            "Missing full dataset prevents full-photo and complete v4 test group review.",
            "No OCR engine, route-reference matching, training or checkpoint loading was used.",
        ],
    }
    (workspace / "review_audit.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(
        "evaluation/ocr_training/v4-reviewed-01-ai-01"
    ))
    args = parser.parse_args()
    result = audit(args.workspace)
    print(json.dumps(result, indent=2))
