"""Synthetic-only crop metrics, review gates, run joins and table exports."""

import csv
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from backend.app.evaluation.crop_scoring import (
    build_report, fingerprint, freeze_manifest, render_html, score_cell, validate_manifest, write_report,
)


class CropScoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def row(self, rid="A001", text="AB CD", **extra):
        return {"review_id": rid, "crop": f"crops/{rid}.png", "image": f"{rid}.jpg",
                "label": "front_eds_destination", "class_id": "3", "annotation_id": rid,
                "crop_sha256": fingerprint(rid), "source_image_sha256": fingerprint("source"+rid),
                "box_xyxy": "[0,0,80,20]", "split": "valid", "transcription": text,
                "legibility": "full", "field_status": "present", "review_status": "reviewed",
                "reviewer": "Synthetic reviewer", "reviewer_type": "human", "reviewed_at": "2026-11-12",
                "human_verification_status": "verified", "human_field_confirmation": "confirmed",
                "human_crop_treatment": "single_field", "field_review_status": "reviewed",
                "group_id": f"scene-{rid}", "group_review_status": "reviewed", "exclusion_reason": "",
                "crop_source": "annotation", "correspondence_status": "", **extra}

    def freeze(self, rows):
        path = self.root / "review.csv"
        columns = list(dict.fromkeys(k for r in rows for k in r))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return freeze_manifest([path])

    def prediction(self, row, text=None, status="success"):
        return {"review_id": row["review_id"], "crop_id": row["crop"],
                "crop_sha256": row["crop_sha256"], "source_image_sha256": row["source_image_sha256"],
                "field": row["label"], "crop_set": row["crop_source"], "status": status,
                "raw_text": row["transcription"] if text is None else text, "crop_total_ms": 10}

    def run_dir(self, predictions, engine="easyocr"):
        path = self.root / engine
        path.mkdir(exist_ok=True)
        (path / "report.json").write_text(json.dumps({"engine": engine, "model": "Synthetic model",
                "reference_matching_used": False, "run_name": "synthetic-01", "actual_device": "synthetic",
                "model_sha256_before": "a"*64, "model_files_sha256": {"weight": "a"*64}}))
        (path / "predictions.jsonl").write_text("\n".join(json.dumps(p) for p in predictions))
        return path

    def config(self, path=None):
        return {"models": [{"id": "easyocr", "baseline": {"run_dir": str(path),
                "splits": ["valid"], "input_sets": ["annotation", "prediction"]} if path else None},
                {"id": "trocr"}, {"id": "paddleocr", "baseline": {"status": "Unavailable"}}]}

    def cell(self, report, model="easyocr", variant="baseline", field="front_eds_destination", population="annotation", split="valid"):
        data = next(m for m in report["models"] if m["id"] == model)
        return next(c for c in data["variants"][variant]["cells"] if
                    (c["field"], c["input_set"], c["split"]) == (field, population, split))

    def test_micro_metrics_have_independent_known_edit_counts(self):
        rows = self.freeze([self.row(), self.row("A002", "X")])["rows"]
        preds = {rows[0]["review_id"]: self.prediction(rows[0], "AB XX CD"),
                 rows[1]["review_id"]: self.prediction(rows[1], "")}
        cell = score_cell(rows, preds, True)
        # First row inserts three characters and one word; second deletes one each.
        self.assertEqual((cell["character_errors"], cell["reference_characters"]), (4, 6))
        self.assertEqual((cell["word_errors"], cell["reference_words"]), (2, 3))
        self.assertAlmostEqual(cell["cer"], 4/6)
        self.assertAlmostEqual(cell["wer"], 2/3)
        self.assertEqual(cell["exact_match"], 0)

    def test_perfect_case_punctuation_and_multiline(self):
        row = self.freeze([self.row(text="Ab.\nRD")])["rows"][0]
        cell = score_cell([row], {"A001": self.prediction(row)}, True)
        self.assertEqual((cell["cer"], cell["wer"], cell["exact_match"]), (0, 0, 1))
        cell = score_cell([row], {"A001": self.prediction(row, "ab RD")}, True)
        self.assertEqual(cell["character_errors"], 3)  # case, period deletion, newline->space
        self.assertEqual(cell["word_errors"], 1)
        self.assertEqual(cell["exact_match"], 0)
        cell = score_cell([row], {"A001": self.prediction(row, "  Ab.  \n RD ")}, True)
        self.assertEqual(cell["exact_match"], 1)

    def test_error_rates_can_exceed_one(self):
        row = self.freeze([self.row(text="A")])["rows"][0]
        cell = score_cell([row], {"A001": self.prediction(row, "A B C D")}, True)
        self.assertEqual(cell["cer"], 6)
        self.assertEqual(cell["wer"], 3)

    def test_gates_ai_partial_group_field_and_correspondence(self):
        changes = [{"reviewer_type": "AI"}, {"text": "A[UNK]", "legibility": "partial"},
                   {"text": "[UNK]", "legibility": "illegible"}, {"group_id": ""},
                   {"field_review_status": "pending"}, {"human_crop_treatment": "challenge"},
                   {"crop_source": "prediction", "correspondence_status": "pending"},
                   {"field_status": "blank", "text": "", "legibility": "not_applicable"},
                   {"field_status": "absent", "text": "", "legibility": "not_applicable"},
                   {"field_status": "wrong_field"}]
        for change in changes:
            with self.subTest(change=change):
                manifest = self.freeze([self.row(**change)])
                self.assertFalse(manifest["rows"][0]["scoring_eligible"])
                self.assertIsNone(score_cell(manifest["rows"], {}, True)["cer"])

    def test_cross_split_group_and_source_hash_overlap_block_both(self):
        for key in ("group_id", "source_image_sha256", "crop_sha256"):
            a, b = self.row(), self.row("A002", split="train")
            b[key] = a[key]
            rows = self.freeze([a, b])["rows"]
            self.assertTrue(all(not r["scoring_eligible"] for r in rows))
            self.assertTrue(all(f"cross_split_{key}" in r["scoring_blockers"] for r in rows))

    def test_failed_and_all_missing_predictions_stay_in_denominator(self):
        manifest = self.freeze([self.row(), self.row("A002")])
        path = self.run_dir([self.prediction(manifest["rows"][0], "misleading partial output", "error")])
        report = build_report(manifest, self.config(path), self.root)
        cell = self.cell(report)
        self.assertEqual((cell["eligible"], cell["failed"], cell["missing"]), (2, 1, 1))
        self.assertEqual((cell["cer"], cell["wer"], cell["exact_match"]), (1, 1, 0))
        path = self.run_dir([])
        self.assertEqual(self.cell(build_report(manifest, self.config(path), self.root))["missing"], 2)

    def test_population_class_variant_and_unrun_statuses(self):
        a = self.row()
        p = self.row("P001", crop_source="prediction", correspondence_status="no_match")
        n = self.row("A002", text="00B", label="front_eds_num")
        manifest = self.freeze([a, p, n])
        path = self.run_dir([self.prediction(r) for r in [a, p, n]])
        config = self.config(path)
        config["models"][0]["finetuned"] = deepcopy(config["models"][0]["baseline"])
        report = build_report(manifest, config, self.root)
        self.assertEqual(self.cell(report)["eligible"], 1)
        self.assertEqual(self.cell(report, population="prediction")["eligible"], 1)
        self.assertEqual(self.cell(report, field="front_eds_num")["exact_match"], 1)
        self.assertEqual(self.cell(report, variant="finetuned")["outcomes"], self.cell(report)["outcomes"])
        self.assertEqual(self.cell(report, model="trocr")["status"], "Not run")
        self.assertEqual(self.cell(report, model="paddleocr")["status"], "Unavailable")
        self.assertEqual(self.cell(report, split="test")["status"], "Not run")
        self.assertEqual(self.cell(report, field="front_eds")["status"], "Not applicable")

    def test_pending_and_no_samples_are_not_zero_accuracy(self):
        row = self.row(reviewer_type="AI")
        manifest = self.freeze([row])
        report = build_report(manifest, self.config(self.run_dir([self.prediction(row)])), self.root)
        self.assertEqual(self.cell(report)["status"], "Review pending")
        self.assertIsNone(self.cell(report)["cer"])
        self.assertEqual(self.cell(report, field="front_eds_route")["status"], "No samples")

    def test_bad_prediction_joins_fail(self):
        row = self.row()
        manifest = self.freeze([row])
        for change in [{"review_id": "unknown"}, {"crop_sha256": "b"*64},
                       {"source_image_sha256": "b"*64}, {"field": "front_eds_num"},
                       {"status": "unknown"}, {"raw_text": None}, {"crop_total_ms": float("nan")}]:
            with self.subTest(change=change):
                pred = {**self.prediction(row), **change}
                with self.assertRaises(ValueError):
                    build_report(manifest, self.config(self.run_dir([pred])), self.root)
        pred = self.prediction(row)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_report(manifest, self.config(self.run_dir([pred, pred])), self.root)

    def test_manifest_tampering_and_duplicate_reviews_fail(self):
        manifest = self.freeze([self.row(reviewer_type="AI")])
        manifest["rows"][0]["scoring_eligible"] = True
        with self.assertRaisesRegex(ValueError, "hash"):
            validate_manifest(manifest)
        manifest["manifest_sha256"] = fingerprint({k:v for k,v in manifest.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(ValueError, "eligibility"):
            validate_manifest(manifest)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.freeze([self.row(), self.row()])

    def test_html_escapes_run_metadata_and_exports_without_overwrite(self):
        manifest = self.freeze([self.row()])
        path = self.run_dir([self.prediction(self.row())])
        meta = json.loads((path/"report.json").read_text())
        meta["model"] = "<script>bad</script>"
        (path/"report.json").write_text(json.dumps(meta))
        report = build_report(manifest, self.config(path), self.root)
        html = render_html(report)
        self.assertEqual(html.count("<table>"), 3)
        self.assertNotIn("<script>", html)
        output = self.root/"output"
        write_report(report, output)
        self.assertEqual(json.loads((output/"report.json").read_text()), report)
        with (output/"summary.csv").open(newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 144)
        with self.assertRaises(FileExistsError):
            write_report(report, output)

    def test_cli_freeze_and_report_without_any_image_files(self):
        self.freeze([self.row(reviewer_type="AI")])
        script = Path(__file__).resolve().parents[2]/"scripts/score_ocr_crops.py"
        manifest = self.root/"frozen.json"
        subprocess.run([sys.executable, str(script), "freeze", "--review", str(self.root/"review.csv"),
                        "--output", str(manifest)], capture_output=True, check=True)
        config = self.root/"config.json"
        config.write_text(json.dumps(self.config()))
        subprocess.run([sys.executable, str(script), "report", "--manifest", str(manifest),
                        "--config", str(config), "--output", str(self.root/"results")], capture_output=True, check=True)
        self.assertTrue((self.root/"results/tables.html").is_file())


if __name__ == "__main__":
    unittest.main()
