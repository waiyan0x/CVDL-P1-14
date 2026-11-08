"""Check lossless submission import and protection of source review work."""

import csv
from pathlib import Path
import tempfile
import unittest

from scripts.import_ocr_transcriptions import import_labels


REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO / "evaluation/ocr_annotations/v4-reviewed-01"
RAW = WORKSPACE / "submissions/codi-01/raw"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class TranscriptionImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.a = RAW / "ocr_labels_A001_A157.csv"
        self.p = RAW / "ocr_labels_P001_P114.csv"

    def run_import(self, output):
        return import_labels(WORKSPACE, self.a, self.p, output, "Codi", "2026-11-07")

    def test_retains_all_text_and_geometry_and_surfaces_contradictions(self):
        output = self.root / "import"
        audit = self.run_import(output)
        for kind, source in (("annotation", self.a), ("prediction", self.p)):
            expected = {r["id"]: r for r in rows(source)}
            templates = {r["review_id"]: r for r in rows(WORKSPACE / "human_review" / f"{kind}_submission.template.csv")}
            imported = rows(output / f"{kind}_codi.csv")
            self.assertEqual(len(imported), len(expected))
            for row in imported:
                submitted = expected[row["review_id"]]
                self.assertEqual(row["transcription"], submitted["text"])
                self.assertEqual(row["legibility"], submitted["quality"])
                for key in ("crop", "image", "label", "box_xyxy", "crop_sha256", "source_image_sha256", "split"):
                    self.assertEqual(row[key], templates[row["review_id"]][key])
                self.assertEqual(row["reviewer"], "Codi")
                self.assertEqual(row["reviewed_at"], "2026-11-07")
            self.assertEqual((output / "raw" / source.name).read_bytes(), source.read_bytes())
        p100 = next(r for r in rows(output / "prediction_codi.csv") if r["review_id"] == "P100")
        self.assertEqual(p100["legibility"], "full")
        self.assertEqual(p100["review_status"], "needs_resolution")
        self.assertIn("full_contains_unknown", p100["issue_codes"])
        self.assertEqual(audit["scoring_ready_rows"], 0)

    def test_repairs_only_overflow_notes_and_preserves_actual_newlines(self):
        output = self.root / "import"
        audit = self.run_import(output)
        imported = {r["review_id"]: r for r in rows(output / "annotation_codi.csv")}
        self.assertEqual(imported["A002"]["notes"], "object occludes left of upper line, lower line clipped")
        self.assertIn("\n", imported["A002"]["transcription"])
        self.assertNotIn("\\n", imported["A002"]["transcription"])
        self.assertEqual(len(audit["mechanical_note_repairs"]), 5)

    def test_refuses_duplicate_ids_without_publishing(self):
        changed = rows(self.a)
        changed[1]["id"] = changed[0]["id"]
        source = self.root / "duplicates.csv"
        with source.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "field", "text", "quality", "note"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(changed)
        output = self.root / "import"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            import_labels(WORKSPACE, source, self.p, output, "Codi", "2026-11-07")
        self.assertFalse(output.exists())

    def test_refuses_existing_import_without_overwriting(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "review.csv"
        sentinel.write_text("human work")
        with self.assertRaises(FileExistsError):
            self.run_import(output)
        self.assertEqual(sentinel.read_text(), "human work")


if __name__ == "__main__":
    unittest.main()
