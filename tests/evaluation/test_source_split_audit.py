import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("source_split_audit", ROOT / "scripts/audit_ocr_source_splits.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceSplitAuditTests(unittest.TestCase):
    def test_test_images_are_not_required_or_read_and_metadata_overlap_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checksums, manifests = {}, []
            for split in ("train", "valid", "test"):
                folder = root / split
                folder.mkdir()
                name = split + ".jpg"
                # The reserved test image deliberately does not exist.
                data = b"same source" if split in {"train", "test"} else b"validation"
                digest = hashlib.sha256(data).hexdigest()
                if split != "test":
                    (folder / name).write_bytes(data)
                coco = folder / "_annotations.coco.json"
                coco.write_text(json.dumps({"images": [{"file_name": name, "extra": {"name": split}}]}))
                checksums[f"{split}/{name}"] = digest
                checksums[f"{split}/_annotations.coco.json"] = module.sha256(coco)
                if split != "test":
                    key = "coco_sha256" if split == "train" else "validation_coco_sha256"
                    manifest = root / (split + ".json")
                    manifest.write_text(json.dumps({"split": split, key: module.sha256(coco),
                                                    "images": [{"image": name, "image_sha256": digest}]}))
                    manifests.append((manifest, key))
            (root / "preparation_manifest.json").write_text(json.dumps({"checksums": checksums}))
            _, _, report = module.audit(root, manifests)
            self.assertEqual(report["test_image_bytes_read"], 0)
            self.assertEqual(report["handoff_mismatches"], [])
            self.assertEqual(report["train_valid_image_hashes_checked"], 2)
            self.assertEqual(len(report["cross_split_links"]), 1)
            self.assertEqual(report["cross_split_links"][0]["link_type"], "declared_sha256")
            (root / "train/train.jpg").write_bytes(b"changed")
            _, _, changed = module.audit(root, manifests)
            self.assertEqual(changed["source_hash_mismatches"], ["train/train.jpg"])
            self.assertEqual(len(changed["handoff_mismatches"]), 1)
            (root / "valid/_annotations.coco.json").write_text('{"images": []}')
            with self.assertRaisesRegex(ValueError, "Unverified COCO"):
                module.audit(root, manifests)


if __name__ == "__main__":
    unittest.main()
