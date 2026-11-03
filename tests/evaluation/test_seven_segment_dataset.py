import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from backend.app.evaluation.seven_segment_dataset import (
    INPUT_COLUMNS, assign_splits, audit_manifest, build_manifest, load_inventory,
)


class SevenSegmentDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def inventory(self, rows):
        path = self.root / "inventory.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=INPUT_COLUMNS)
            writer.writeheader()
            for index, row in enumerate(rows):
                image = self.root / f"sample-{index}.png"
                Image.new("L", (12, 6), index * 45).save(image)
                writer.writerow({"sample_id": f"sample-{index}", "crop_path": image.name,
                                 "display_group_id": f"display-{index}",
                                 "recording_id": f"recording-{index}", "frame_index": index,
                                 "field_name": "voltage", "truth_raw": str(index + 1),
                                 "label_status": "readable", "primary_reviewer": "Alice",
                                 "secondary_reviewer": "Bob", "augmented_from": "", **row})
        return path

    def test_manifest_has_three_group_safe_splits_and_reviewed_truth(self):
        inventory = self.inventory([{}, {}, {}, {}])
        manifest = build_manifest(inventory, dataset_id="meter-crops", version="v1")
        self.assertEqual(manifest["dataset"]["status"], "draft")
        self.assertEqual(set(row["split"] for row in manifest["samples"]), {"train", "val", "test"})
        self.assertTrue(manifest["audit"]["ready_for_evaluation"])
        self.assertEqual(manifest["audit"]["issues"], [])
        self.assertTrue(all(len(row["crop_sha256"]) == 64 for row in manifest["samples"]))
        self.assertTrue(all((row["input_width"], row["input_height"]) == (12, 6)
                            for row in manifest["samples"]))

    def test_shared_recording_and_augmentation_stay_in_same_split(self):
        inventory = self.inventory([{}, {"recording_id": "recording-0"},
                                    {"augmented_from": "sample-0"}, {}, {}])
        rows = assign_splits(load_inventory(inventory))
        self.assertEqual(rows[0]["split"], rows[1]["split"])
        self.assertEqual(rows[0]["split"], rows[2]["split"])

    def test_unreviewed_validation_or_test_label_fails_readiness(self):
        inventory = self.inventory([{"secondary_reviewer": ""}, {}, {}])
        rows = assign_splits(load_inventory(inventory))
        if rows[0]["split"] == "train":
            rows[0]["split"], rows[1]["split"] = rows[1]["split"], rows[0]["split"]
        audit = audit_manifest(rows)
        self.assertFalse(audit["ready_for_evaluation"])
        self.assertTrue(any("second review" in issue for issue in audit["issues"]))

    def test_invalid_readable_truth_is_rejected(self):
        inventory = self.inventory([{"truth_raw": "1O"}, {}, {}])
        with self.assertRaises(ValueError):
            load_inventory(inventory)

    def test_exact_duplicate_crop_across_splits_fails_readiness(self):
        inventory = self.inventory([{}, {}, {}])
        rows = assign_splits(load_inventory(inventory))
        rows[1]["crop_sha256"] = rows[0]["crop_sha256"]
        audit = audit_manifest(rows)
        self.assertFalse(audit["ready_for_evaluation"])
        self.assertTrue(any("crop hash" in issue for issue in audit["issues"]))

    def test_edited_manifest_cannot_move_augmentation_to_test(self):
        inventory = self.inventory([{}, {"augmented_from": "sample-0"}, {}, {}])
        rows = assign_splits(load_inventory(inventory))
        rows[1]["split"] = "test" if rows[0]["split"] != "test" else "val"
        audit = audit_manifest(rows)
        self.assertFalse(audit["ready_for_evaluation"])
        self.assertTrue(any("augmentation sample-1" in issue for issue in audit["issues"]))


if __name__ == "__main__":
    unittest.main()
