import hashlib
import json

import pytest

from backend.app.evaluation.manifest import load_manifest, select_images
from backend.app.evaluation.provenance import dataset_audit


def manifest_for(tmp_path, reviewed=True):
    image = tmp_path / "image.jpg"
    image.write_bytes(b"reviewed test image")
    data = {"schema_version": 1, "dataset": {"id": "fixture", "version": "1", "split": "test"},
            "review": {"reviewed": reviewed, "reviewer": "Test reviewer", "reviewed_at": "2026-10-22"},
            "images": [{"id": "frame-1", "path": "image.jpg", "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                        "displays": [{"id": "display-1", "box": [0, 0, 100, 40],
                                      "bus_number": "3", "destination": None}]}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return path, data


def test_manifest_requires_human_review_and_exact_image_identity(tmp_path):
    path, data = manifest_for(tmp_path, reviewed=False)
    with pytest.raises(ValueError, match="review"):
        load_manifest(path)
    data["review"]["reviewed"] = True
    data["images"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="hash"):
        load_manifest(path)


def test_manifest_excludes_training_overlap_and_repeated_images(tmp_path):
    path, data = manifest_for(tmp_path)
    training = tmp_path / "project/data/images/train"
    training.mkdir(parents=True)
    (training / "renamed.jpg").write_bytes((tmp_path / "image.jpg").read_bytes())
    manifest = load_manifest(path)
    selected, excluded = select_images(manifest, tmp_path / "project")
    assert selected == []
    assert excluded[0]["reason"] == "training_overlap"


def test_audit_counts_unique_overlap_images_not_pairs(tmp_path):
    for split in ("train", "val", "test"):
        (tmp_path / "data/images" / split).mkdir(parents=True)
        (tmp_path / "data/labels" / split).mkdir(parents=True)
    for name, content in (("one.jpg", b"same"), ("two.jpg", b"same")):
        (tmp_path / "data/images/train" / name).write_bytes(content)
    (tmp_path / "data/images/test/copy.jpg").write_bytes(b"same")
    audit = dataset_audit(tmp_path)
    overlap = next(item for item in audit["overlap"] if item["splits"] == ["train", "test"])
    assert overlap["image_count"] == 1
    assert len(overlap["groups"][0]["train"]) == 2
