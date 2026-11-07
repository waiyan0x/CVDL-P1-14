"""Contract checks for preparing the actual immutable v4 review package."""

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.prepare_ocr_annotations import ORIGINAL_COLUMNS, prepare


REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO / "evaluation/ocr_annotations/v4-reviewed-01"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class AnnotationPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        shutil.copytree(WORKSPACE / "source", self.source)
        self.output = self.root / "output"
        self.output.mkdir()

    def test_preserves_template_and_does_not_assert_prediction_truth(self):
        audit = prepare(self.source, self.output, {"test": True})
        original = read_csv(self.source / "transcriptions_template.csv")
        annotation = read_csv(self.output / "annotation_review.csv")
        self.assertEqual([{key: row[key] for key in ORIGINAL_COLUMNS} for row in annotation], original)
        self.assertEqual(len(annotation), 157)
        predicted = read_csv(self.output / "prediction_review.csv")
        self.assertEqual(len(predicted), 114)
        self.assertEqual(sum(bool(row["candidate_gt_crop"]) for row in predicted), 87)
        for row in annotation + predicted:
            self.assertEqual(row["transcription"], "")
            self.assertEqual(row["review_status"], "pending")
            self.assertEqual(row["reviewer"], "")
            self.assertEqual(row["field_status"], "")
            self.assertEqual(row["split"], "valid")
        images = read_csv(self.output / "image_review.csv")
        self.assertEqual(len(images), 53)
        self.assertEqual(sum(row["source_zero_box"] == "true" for row in images), 10)
        self.assertEqual(audit["human_reviewed_rows"], 0)

    def test_rejects_template_field_mismatch(self):
        path = self.source / "transcriptions_template.csv"
        content = path.read_text(encoding="utf-8-sig")
        path.write_text(content.replace(",front_eds_num,,pending", ",front_eds_route,,pending", 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            prepare(self.source, self.output, {})

    def test_rejects_geometry_that_does_not_match_crop(self):
        path = self.source / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["images"][0]["ground_truth"][0]["box_xyxy"][2] += 1
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Crop size differs"):
            prepare(self.source, self.output, {})

    def test_refuses_reviewed_source_instead_of_erasing_review(self):
        path = self.source / "transcriptions_template.csv"
        content = path.read_text(encoding="utf-8-sig")
        path.write_text(content.replace(",,pending", ",96B,reviewed", 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "preserve existing review"):
            prepare(self.source, self.output, {})

    def test_cli_refuses_existing_workspace_without_modification(self):
        marker = self.output / "review.csv"
        marker.write_text("human work\n")
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts/prepare_ocr_annotations.py"), "--output", str(self.output)],
            cwd=REPO, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(marker.read_text(), "human work\n")


if __name__ == "__main__":
    unittest.main()
