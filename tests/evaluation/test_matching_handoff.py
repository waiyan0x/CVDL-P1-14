import csv
import json
from pathlib import Path
import unittest
import zipfile

from backend.app.evaluation.crop_scoring import build_report, write_report
from backend.app.evaluation.review_decisions import digest
from scripts.prepare_ocr_matching_handoff import prepare
from tests.evaluation import test_crop_scoring


class MatchingHandoffTests(unittest.TestCase):
    def setUp(self):
        helper = test_crop_scoring.CropScoringTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        self.root = helper.root
        rows = [helper.row(text="REFERENCE SECRET", reviewer_type="AI"),
                helper.row("P001", crop_source="prediction", user_scope_policy="challenge_only",
                           detector_confidence="0.7", exclusion_reason="challenge")]
        manifest = helper.freeze(rows)
        preds = [dict(helper.prediction(rows[0], "  00B\nRD. "), ocr_confidence=.8),
                 dict(helper.prediction(rows[1], "diagnostic only", "error"), error="failed", ocr_confidence=None)]
        self.run = helper.run_dir(preds)
        config = helper.config(self.run)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(config))
        self.report = self.root / "scoring"
        write_report(build_report(manifest, config, self.root), self.report)
        (self.report / "manifest.json").write_text(json.dumps(manifest))
        self.reference = self.root / "reference.csv"
        self.reference.write_text("Route number,Origin,Destination\n00B,A,B\n00B,A,B\n2,C,\n")
        self.guide = self.root / "guide.md"
        self.guide.write_text("Read matching_inputs.jsonl; evaluation is separate.")
        self.output = self.root / "handoff"

    def prepare(self):
        return prepare(self.report, self.config, self.reference, self.guide, self.output)

    def test_portable_bundle_preserves_failures_and_excludes_reference_labels_from_inputs(self):
        summary = self.prepare()
        inputs_text = (self.output / "matching_inputs.jsonl").read_text()
        self.assertNotIn("REFERENCE SECRET", inputs_text)
        records = [json.loads(s) for s in inputs_text.splitlines()]
        self.assertEqual(records[0]["raw_ocr_text"], "  00B\nRD. ")
        self.assertEqual(records[0]["normalised_ocr_text"], "00b rd.")
        self.assertIsNone(records[0]["display_id"])
        self.assertEqual(records[1]["raw_ocr_text"], "diagnostic only")
        self.assertFalse(records[1]["successful_nonempty_input"])
        self.assertEqual(records[1]["scope_policy"], "challenge_only")
        self.assertEqual(records[1]["detector_confidence"], .7)
        self.assertEqual(summary["statuses"], {"success": 1, "error": 1})
        self.assertEqual(summary["reference_audit"]["duplicate_full_rows"], 1)
        self.assertEqual(summary["reference_audit"]["blank_cells"]["Destination"], 1)
        for name, expected in summary["files_sha256"].items():
            self.assertEqual(digest(self.output / name), expected)
        with (self.output / "matching_outputs.template.csv").open(newline="") as handle:
            self.assertTrue(all(r["matching_status"] == "pending" and not r["matched_endpoint"]
                                for r in csv.DictReader(handle)))
        with zipfile.ZipFile(self.output.with_suffix(".zip")) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("handoff/matching_inputs.jsonl", archive.namelist())
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_changed_saved_predictions_and_reserved_split_are_rejected(self):
        path = self.run / "predictions.jsonl"
        before = path.read_text()
        path.write_text(before.replace("diagnostic only", "changed"))
        with self.assertRaisesRegex(ValueError, "Saved run changed"):
            self.prepare()
        self.assertFalse(self.output.exists())
        path.write_text(before)
        manifest = json.loads((self.report / "manifest.json").read_text())
        # Re-freeze a genuine reserved split instead of forging a manifest hash.
        helper = test_crop_scoring.CropScoringTests()
        helper.root = self.root
        manifest = helper.freeze([helper.row(split="test")])
        (self.report / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "test remains reserved"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
