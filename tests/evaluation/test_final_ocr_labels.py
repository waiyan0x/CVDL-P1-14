import unittest

from scripts.prepare_final_ocr_labels import select


class FinalOCRLabelsTests(unittest.TestCase):
    def triplet(self, **changes):
        return [dict(review_id=f"T{i}", image=f"aug{i}.jpg", source_name="source.jpg",
                     label="front_eds_num", legibility="full", transcription="097E",
                     user_scope_policy="review_required", **changes) for i in range(3)]

    def test_literal_three_copy_agreement_preserves_leading_zero(self):
        rows = self.triplet()
        selected, held = select(rows)
        self.assertEqual([r["transcription"] for r in selected], ["097E"] * 3)
        self.assertEqual(held, [])
        rows[2]["transcription"] = "97E"
        self.assertEqual(select(rows), ([], []))

    def test_missing_copy_and_duplicate_image_do_not_make_a_triplet(self):
        rows = self.triplet()
        self.assertEqual(select(rows[:2]), ([], []))
        rows[2]["image"] = rows[1]["image"]
        self.assertEqual(select(rows), ([], []))

    def test_quarantine_requires_clearance_and_unknowns_are_excluded(self):
        rows = self.triplet(training_disposition="quarantined_legacy_holdout_candidate")
        selected, held = select(rows)
        self.assertEqual((len(selected), len(held)), (0, 3))
        self.assertEqual(len(select(rows, quarantine_cleared=True)[0]), 3)
        rows[0]["transcription"] = "[UNK]"
        self.assertEqual(select(rows), ([], []))


if __name__ == "__main__":
    unittest.main()
