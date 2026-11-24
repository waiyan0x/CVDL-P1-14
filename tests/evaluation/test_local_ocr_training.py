"""Legacy source mapping, quarantine and crop-provenance checks."""

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts.prepare_local_ocr_training import parse_boxes, prepare, source_key


REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "evaluation/ocr_training/local88-01"


class LocalOCRTrainingTests(unittest.TestCase):
    def test_roboflow_source_key_keeps_original_photo_identity(self):
        self.assertEqual(source_key("14488614-bus_8_jpg.rf.abc123.jpg"), source_key("14488614-bus_8.jpg"))
        self.assertNotEqual(source_key("photo_bus_8.jpg"), source_key("different_bus_8.jpg"))

    def test_yolo_boxes_are_clipped_and_empty_boxes_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "labels.txt"
            path.write_text("1 0.95 0.5 0.2 0.4\n")
            self.assertEqual(parse_boxes(path, (100, 100)), [(1, 1, [85, 30, 100, 70])])
            path.write_text("1 0.5 0.5 0 0.4\n")
            with self.assertRaises(ValueError):
                parse_boxes(path, (100, 100))

    def test_every_holdout_connected_training_image_is_quarantined(self):
        audit = json.loads((PACKAGE / "audit.json").read_text())
        sources = {row["source_id"]: row for row in audit["sources"]}
        for group in audit["groups"]:
            for source_id in group["members"]:
                row = sources[source_id]
                if row["split"] == "train" and group["holdout_link"]:
                    self.assertEqual(row["training_disposition"], "excluded_holdout_link")
        self.assertEqual(audit["training_ready_rows"], 0)

    def test_exported_crops_retain_source_hashes_geometry_and_pending_state(self):
        with (PACKAGE / "transcriptions.template.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 179)
        self.assertEqual(len({row["crop_id"] for row in rows}), 179)
        self.assertEqual({row["field"] for row in rows}, {"front_eds_num", "front_eds_destination"})
        for row in rows:
            source = REPO / row["source_image"]
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), row["source_image_sha256"])
            crop = PACKAGE / row["crop_id"]
            self.assertEqual(hashlib.sha256(crop.read_bytes()).hexdigest(), row["crop_sha256"])
            x1, y1, x2, y2 = json.loads(row["bbox"])
            with Image.open(crop) as image:
                self.assertEqual(image.size, (x2-x1, y2-y1))
            self.assertEqual(row["text"], "")
            self.assertEqual(row["reviewer"], "")
            self.assertEqual(row["review_status"], "pending")

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "review.csv"
            marker.write_text("existing labels")
            with self.assertRaises(FileExistsError):
                prepare(REPO, output)
            self.assertEqual(marker.read_text(), "existing labels")


if __name__ == "__main__":
    unittest.main()
