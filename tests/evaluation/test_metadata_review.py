"""Synthetic metadata adjudication must not manufacture review or lose exclusions."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from backend.app.evaluation.metadata_review import ReviewBundle
from backend.app.evaluation.review_decisions import create_template, read_rows, digest


class MetadataReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "review.csv"
        self.group_source = self.root / "groups.csv"
        self.pair_source = self.root / "pairs.csv"
        self.registry = self.root / "registry.csv"
        self.forms = self.root / "forms"
        self.output = self.root / "result"
        base = dict(crop="a.png", image="one.jpg", label="front_eds_num", class_id="1",
                    annotation_id="1", source_image_sha256="a" * 64, box_xyxy="[0,0,20,10]",
                    split="valid", crop_sha256="b" * 64, transcription="00A", legibility="full",
                    field_status="present", review_status="reviewed", reviewer="Synthetic person",
                    reviewer_type="human", reviewed_at="2026-11-15", human_verification_status="verified",
                    human_field_confirmation="confirmed", human_crop_treatment="single_field",
                    field_review_status="reviewed",
                    group_id="", group_review_status="pending", correspondence_status="pending",
                    exclusion_reason="", training_ready="false")
        self.rows = [dict(base, review_id="A001", crop_source="annotation"),
                     dict(base, review_id="P001", crop_source="prediction", crop="p.png", crop_sha256="c" * 64),
                     dict(base, review_id="T001", split="train", image="two.jpg", source_image_sha256="d" * 64,
                          crop="t.png", crop_sha256="e" * 64, crop_source="annotation")]
        self.write(self.source, self.rows)
        self.groups = [dict(split=s, image=i, source_name=i, source_image_sha256=h, family_id=f,
                            human_group_id="", human_group_decision="", human_reviewer="",
                            human_reviewed_at="", human_notes="") for s, i, h, f in
                       [("valid", "one.jpg", "a" * 64, "F1"), ("train", "two.jpg", "d" * 64, "F2")]]
        self.write(self.group_source, self.groups)
        self.write(self.registry, [dict(split=r["split"], image=r["image"], source_name=r["source_name"],
                                        declared_sha256=r["source_image_sha256"]) for r in self.groups])
        self.write(self.pair_source, [dict(prediction_id="P001", annotation_id="A001", prediction_class="front_eds_num",
                  prediction_crop="p.png", source_image="one.jpg", crop_sha256="c" * 64,
                  annotation_crop="a.png", annotation_crop_sha256="b" * 64, source_review_sha256=digest(self.source),
                  iou="1", human_correspondence="", human_reviewer="", human_reviewed_at="", human_notes="")])
        self.bundle().prepare(self.forms)
        self.g = self.load(self.forms / "photo_group_decisions.csv")
        self.p = self.load(self.forms / "crop_pairing_decisions.csv")

    def write(self, path, rows):
        columns = list(dict.fromkeys(k for r in rows for k in r))
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)

    def load(self, path):
        with path.open(newline="") as f:
            return list(csv.DictReader(f))

    def bundle(self, policies=()):
        return ReviewBundle([self.source], policies, self.group_source, self.pair_source, self.registry)

    def attest(self, row):
        row.update(human_reviewer="Synthetic reviewer", human_reviewer_type="human",
                   human_reviewed_at="2026-11-15", human_notes="Synthetic inspection")

    def run_import(self, bundle=None, dry=False, text=()):
        self.write(self.forms / "photo_group_decisions.csv", self.g)
        self.write(self.forms / "crop_pairing_decisions.csv", self.p)
        return (bundle or self.bundle()).apply(self.forms / "photo_group_decisions.csv",
                 self.forms / "crop_pairing_decisions.csv", self.output, text, dry)

    def confirm(self, cross=False):
        for i, g in enumerate(self.g):
            self.attest(g); g.update(human_group_decision="confirm", human_group_id="shared" if cross else f"scene-{i}")
        self.attest(self.p[0]); self.p[0]["human_correspondence"] = "same_visible_text"

    def test_blank_templates_preserve_pending_without_promotion(self):
        before = self.source.read_bytes()
        result = self.run_import()
        self.assertEqual(result["validation_eligible"], 2)
        self.assertEqual(result["decisions_applied"], {})
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result["training_ready_rows"], 0)

    def test_confirmed_groups_propagate_to_annotation_and_prediction(self):
        self.confirm()
        result = self.run_import()
        self.assertEqual(result["validation_eligible"], 2)
        rr = self.load(self.output / "valid.review.csv")
        self.assertEqual({r["group_id"] for r in rr}, {"scene-0"})
        self.assertEqual(rr[1]["transcription"], "00A")
        self.assertTrue(all(r["training_ready"] == "false" for r in rr))

    def test_cross_split_group_is_recorded_without_gating_project_scores(self):
        self.confirm(cross=True)
        result = self.run_import()
        self.assertEqual(result["cross_split_groups"], ["shared"])
        self.assertEqual(result["validation_eligible"], 2)
        self.assertEqual(result["validation_excluded"], 2)

    def test_registry_test_hash_links_exclude_without_pixels(self):
        reg = self.load(self.registry)
        reg.append(dict(reg[0], split="test", image="test.jpg"))
        self.write(self.registry, reg)
        binding = self.bundle().binding
        for r in self.g + self.p: r["source_bundle_sha256"] = binding
        self.confirm()
        result = self.run_import()
        self.assertEqual(result["validation_eligible"], 2)
        self.assertFalse(result["image_pixels_accessed"])

    def test_changed_hash_binding_ai_identity_and_missing_date_rejected(self):
        self.confirm()
        for key, value in [("crop_sha256", "f" * 64), ("source_bundle_sha256", "f" * 64),
                           ("human_reviewer_type", "AI"), ("human_reviewed_at", ""), ("human_notes", "")]:
            with self.subTest(key=key):
                old = self.p[0][key]; self.p[0][key] = value
                with self.assertRaises(ValueError): self.run_import()
                self.assertFalse(self.output.exists()); self.p[0][key] = old

    def test_unrelated_pair_zero_overlap_and_wrong_target_hash_rejected(self):
        self.confirm()
        for changes in [dict(annotation_id="T001"), dict(annotation_crop_sha256="f" * 64)]:
            old = dict(self.p[0]); self.p[0].update(changes)
            with self.assertRaises(ValueError): self.run_import()
            self.p[0] = old
        self.rows[1]["box_xyxy"] = "[30,0,40,10]"
        self.write(self.source, self.rows)
        for r in self.g + self.p: r["source_bundle_sha256"] = self.bundle().binding
        with self.assertRaisesRegex(ValueError, "overlap"): self.run_import()

    def test_no_match_requires_empty_annotation_and_keeps_own_truth(self):
        self.confirm(); self.p[0]["human_correspondence"] = "no_match"
        with self.assertRaisesRegex(ValueError, "no_match"): self.run_import()
        self.p[0].update(annotation_id="", annotation_crop="", annotation_crop_sha256="")
        self.assertEqual(self.run_import()["validation_eligible"], 2)

    def test_partial_group_submission_does_not_mark_untouched_sources_reviewed(self):
        self.confirm(); self.g = self.g[:1]
        self.run_import()
        train = self.load(self.output / "train.review.csv")[0]
        self.assertEqual(train["group_review_status"], "pending")

    def test_conflicting_groups_for_exact_source_family_rejected(self):
        self.groups[1]["source_name"] = "one.jpg"
        self.write(self.group_source, self.groups)
        reg = self.load(self.registry); reg[1]["source_name"] = "one.jpg"; self.write(self.registry, reg)
        self.g[1]["source_name"] = "one.jpg"
        for r in self.g + self.p: r["source_bundle_sha256"] = self.bundle().binding
        self.confirm()
        with self.assertRaisesRegex(ValueError, "Conflicting groups"): self.run_import()

    def test_duplicate_metadata_and_incomplete_decisions_are_rejected(self):
        self.g.append(dict(self.g[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"): self.run_import()
        self.g.pop(); self.attest(self.g[0])
        with self.assertRaisesRegex(ValueError, "without a decision"): self.run_import()

    def test_text_import_uses_original_binding_and_preserves_later_policy(self):
        policy = self.root / "policy.csv"
        self.write(policy, [dict(r, exclusion_reason="Keep challenge") for r in self.rows])
        bundle = self.bundle([policy])
        for r in self.g + self.p: r["source_bundle_sha256"] = bundle.binding
        text = self.root / "text.csv"; create_template(self.source, text)
        rr = read_rows(text)[1]; d = rr[0]
        self.attest(d); d.update(human_decision="exclude", human_field_confirmation="needs_resolution",
                                human_crop_treatment="challenge")
        self.write(text, rr)
        self.run_import(bundle, text=[text])
        output = self.load(self.output / "valid.review.csv")[0]
        self.assertIn("Keep challenge", output["exclusion_reason"])
        self.assertIn("Synthetic inspection", output["exclusion_reason"])
        self.assertEqual(output["transcription"], "00A")

    def test_dry_run_is_repeatable_and_overwrite_protected(self):
        self.confirm(); bundle = self.bundle()
        a = self.run_import(bundle, dry=True); self.assertFalse(self.output.exists())
        b = self.run_import(bundle)
        self.assertEqual(a["validation_eligible"], b["validation_eligible"])
        with self.assertRaises(FileExistsError): self.run_import()

    def test_same_text_conflict_is_not_silently_accepted(self):
        self.rows[1]["transcription"] = "Other"
        self.write(self.source, self.rows)
        for r in self.g + self.p: r["source_bundle_sha256"] = self.bundle().binding
        self.confirm()
        with self.assertRaisesRegex(ValueError, "verified transcriptions"): self.run_import()

    def test_source_policy_preserves_exclusions_for_photos_without_text(self):
        extra = dict(self.groups[0], image="negative.jpg", source_name="negative.jpg",
                     source_image_sha256="f" * 64, family_id="F3")
        groups = self.groups + [extra]
        self.write(self.group_source, groups)
        self.write(self.registry, [dict(split=r["split"], image=r["image"], source_name=r["source_name"],
                                        declared_sha256=r["source_image_sha256"]) for r in groups])
        policy = self.root / "source-policy.csv"
        self.write(policy, [dict(r, benchmark_split_treatment="exclude_unverified_cross_split_scene",
                                benchmark_split_treatment_basis="Keep scene quarantine") for r in groups])
        bundle = ReviewBundle([self.source], [], self.group_source, self.pair_source, self.registry, policy)
        self.confirm()
        for r in self.g + self.p: r["source_bundle_sha256"] = bundle.binding
        result = self.run_import(bundle)
        self.assertEqual(result["source_photos_excluded_by_policy"], 3)
        self.assertEqual(result["validation_eligible"], 2)
        rr = self.load(self.output / "source_groups.csv")
        self.assertEqual({r["split_treatment"] for r in rr}, {"excluded_by_existing_policy"})


if __name__ == "__main__":
    unittest.main()
