"""Synthetic review imports protect identity, human provenance and eligibility."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from backend.app.evaluation.review_decisions import (
    DECISION_COLUMNS, create_template, import_decisions, read_rows,
)


class ReviewDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.csv"
        self.decisions = self.root / "decisions.csv"
        self.output = self.root / "export"
        self.original = {
            "review_id": "A001", "crop": "ground_truth/destination/sample.png",
            "image": "sample.png", "label": "front_eds_destination", "class_id": "3",
            "annotation_id": "7", "crop_sha256": "a" * 64,
            "source_image_sha256": "b" * 64, "box_xyxy": "[0,0,80,20]", "split": "valid",
            "transcription": "Old", "legibility": "full", "field_status": "present",
            "review_status": "needs_resolution", "reviewer": "Codex", "reviewer_type": "AI",
            "human_verification_status": "pending", "crop_source": "annotation",
            "group_id": "", "group_review_status": "pending", "correspondence_status": "",
            "exclusion_reason": "", "notes": "Original note", "training_ready": "false",
        }
        self.prepare()

    def write(self, path, rows, columns=None):
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def prepare(self, **changes):
        self.original.update(changes)
        self.write(self.source, [self.original])
        self.decisions.unlink(missing_ok=True)
        create_template(self.source, self.decisions)
        self.decision = read_rows(self.decisions)[1][0]
        self.decision.update(human_decision="correct", final_transcription="00A\nNew Rd.",
                             final_legibility="full", final_field_status="present",
                             human_field_confirmation="confirmed", human_crop_treatment="single_field",
                             human_reviewer="Synthetic reviewer", human_reviewer_type="human",
                             human_reviewed_at="2026-11-12", human_notes="Synthetic visual correction")

    def run_import(self, dry_run=False):
        self.write(self.decisions, [self.decision], DECISION_COLUMNS)
        return import_decisions(self.source, self.decisions, self.output, dry_run)

    def test_round_trip_preserves_source_identity_and_audits_correction(self):
        before = self.source.read_bytes()
        audit = self.run_import()
        result = read_rows(self.output / "review.csv")[1][0]
        self.assertEqual(self.source.read_bytes(), before)
        for key in ("label", "class_id", "box_xyxy", "split", "crop_sha256", "group_review_status"):
            self.assertEqual(result[key], self.original[key])
        self.assertEqual(result["transcription"], "00A\nNew Rd.")
        self.assertEqual(result["reviewer_type"], "human")
        self.assertEqual(result["scoring_ready"], "false")
        self.assertEqual(result["training_ready"], "false")
        self.assertEqual(audit["blocker_counts"], {"group_review_pending": 1})
        change = json.loads((self.output / "change_log.json").read_text())[0]
        self.assertEqual(change["before"]["transcription"], "Old")
        self.assertEqual(change["after"]["transcription"], "00A\nNew Rd.")
        self.assertEqual(change["after"], result)

    def test_template_has_blank_human_attestation_and_refuses_overwrite(self):
        template = self.root / "blank.csv"
        self.assertEqual(create_template(self.source, template), 1)
        row = read_rows(template)[1][0]
        self.assertEqual(row["human_reviewer_type"], "")
        self.assertEqual(row["final_transcription"], "")
        with self.assertRaises(FileExistsError):
            create_template(self.source, template)

    def test_dry_run_and_blank_decisions_publish_nothing(self):
        audit = self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())
        self.assertEqual(audit["decisions_applied"], 1)
        blank = self.root / "blank.csv"
        create_template(self.source, blank)
        audit = import_decisions(self.source, blank, dry_run=True)
        self.assertEqual(audit["decisions_applied"], 0)
        self.assertIn("human_review_incomplete", audit["blocker_counts"])

    def test_all_gates_allow_scoring_but_never_training_promotion(self):
        self.prepare(group_id="scene-1", group_review_status="reviewed", split="train")
        audit = self.run_import()
        self.assertEqual(audit["scoring_ready_rows"], 1)
        self.assertEqual(audit["training_ready_rows"], 0)

    def test_predicted_correspondence_stays_pending(self):
        self.prepare(review_id="P001", crop_source="prediction", group_id="scene-1",
                     group_review_status="reviewed", correspondence_status="pending")
        audit = self.run_import()
        self.assertEqual(audit["blocker_counts"], {"correspondence_pending": 1})

    def test_challenge_crop_stays_out_of_primary_scoring(self):
        self.prepare(group_id="scene-1", group_review_status="reviewed")
        self.decision["human_crop_treatment"] = "challenge"
        self.assertEqual(self.run_import()["scoring_ready_rows"], 0)

    def test_ai_identity_or_missing_human_metadata_is_rejected(self):
        for key, value in [("human_reviewer_type", "AI"), ("human_reviewer", ""),
                           ("human_reviewed_at", "not-a-date"), ("human_notes", "")]:
            with self.subTest(key=key):
                original = self.decision[key]
                self.decision[key] = value
                with self.assertRaises(ValueError):
                    self.run_import()
                self.assertFalse(self.output.exists())
                self.decision[key] = original

    def test_contradictory_or_invalid_text_is_rejected(self):
        for text, legibility in [("[UNK]", "full"), ("Text", "partial"),
                                 ("Text", "illegible"), ("A\\nB", "full"),
                                 (" A", "full"), ("A\n\nB", "full"),
                                 ("A\u00a0B", "full"), ("e\u0301", "full")]:
            with self.subTest(text=text, legibility=legibility):
                self.decision.update(final_transcription=text, final_legibility=legibility)
                with self.assertRaises(ValueError):
                    self.run_import()
                self.assertFalse(self.output.exists())

    def test_explicit_blank_and_partial_are_reviewed_but_unscored(self):
        self.decision.update(final_transcription="", final_legibility="not_applicable", final_field_status="blank")
        audit = self.run_import(dry_run=True)
        self.assertEqual(audit["scoring_ready_rows"], 0)
        self.decision.update(final_transcription="A[UNK]", final_legibility="partial", final_field_status="present")
        self.assertIn("text_not_full", self.run_import(dry_run=True)["blocker_counts"])

    def test_exclusion_and_unresolved_decisions_preserve_text(self):
        for action in ("exclude", "needs_resolution"):
            self.decision.update(human_decision=action, final_transcription="",
                                 final_legibility="", final_field_status="")
            self.assertEqual(self.run_import(dry_run=True)["scoring_ready_rows"], 0)

    def test_accept_rejects_conflicting_final_values(self):
        self.decision["human_decision"] = "accept"
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.run_import()
        self.decision.update(final_transcription="", final_legibility="", final_field_status="")
        self.assertEqual(self.run_import()["decisions_applied"], 1)

    def test_hash_mismatch_unknown_id_and_unused_values_fail(self):
        for key, value in [("crop_sha256", "c" * 64), ("source_review_sha256", "d" * 64),
                           ("review_id", "A999"), ("human_decision", "")]:
            with self.subTest(key=key):
                prior = self.decision[key]
                self.decision[key] = value
                with self.assertRaises(ValueError):
                    self.run_import()
                self.assertFalse(self.output.exists())
                self.decision[key] = prior

    def test_duplicate_ids_and_source_geometry_fail(self):
        self.write(self.decisions, [self.decision, self.decision], DECISION_COLUMNS)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            import_decisions(self.source, self.decisions, self.output)
        self.original["box_xyxy"] = "[0,0,0,20]"
        self.write(self.source, [self.original])
        with self.assertRaisesRegex(ValueError, "geometry"):
            self.run_import()

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("existing human work")
        with self.assertRaises(FileExistsError):
            self.run_import()
        self.assertEqual(sentinel.read_text(), "existing human work")

    def test_invalid_later_decision_never_publishes_earlier_changes(self):
        other = dict(self.original, review_id="A002")
        self.write(self.source, [self.original, other])
        self.decisions.unlink()
        create_template(self.source, self.decisions)
        decisions = read_rows(self.decisions)[1]
        for d in decisions:
            d.update({k: v for k, v in self.decision.items()
                      if k not in {"review_id", "source_review_sha256", "crop_sha256"}})
        decisions[1]["human_reviewer_type"] = "AI"
        self.write(self.decisions, decisions, DECISION_COLUMNS)
        before = self.source.read_bytes()
        with self.assertRaises(ValueError):
            import_decisions(self.source, self.decisions, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), before)

    def test_preexisting_verified_row_still_needs_valid_text_and_reviewer_date(self):
        self.prepare(transcription="[UNK]", reviewer_type="human", review_status="reviewed",
                     human_verification_status="verified", human_field_confirmation="confirmed",
                     human_crop_treatment="single_field", group_id="scene-1", group_review_status="reviewed")
        blank = self.root / "blank.csv"
        create_template(self.source, blank)
        audit = import_decisions(self.source, blank, dry_run=True)
        self.assertEqual(audit["scoring_ready_rows"], 0)
        self.assertIn("human_review_incomplete", audit["blocker_counts"])
        self.assertIn("text_or_field_conventions_unresolved", audit["blocker_counts"])


if __name__ == "__main__":
    unittest.main()
