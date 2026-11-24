"""Table views must expose real denominators and never manufacture metrics."""

import unittest
from scripts.prepare_ocr_template_tables import render_tables, table_rows


class TemplateTableTests(unittest.TestCase):
    def fixture(self, eligible=0):
        models = [{"id": k, "name": k} for k in ("easyocr", "trocr", "paddleocr")]
        rows = [dict(model=m["id"], scoring_mode=mode, input_set=pop, split="valid",
                     crop_class="front_eds_num", crops=10, eligible=eligible,
                     status="Scored" if eligible else "Review pending",
                     cer=.125 if eligible else None, wer=.25 if eligible else None,
                     exact_match=.75 if eligible else None)
                for m in models for mode in ("raw", "normalised") for pop in ("annotation", "prediction")]
        return rows, models

    def test_exactly_three_tables_with_pending_scores_and_view_controls(self):
        rows, models = self.fixture()
        page = render_tables(rows, models)
        self.assertEqual(page.count('<table>'), 3)
        self.assertIn('Review pending', page)
        self.assertIn('id="mode"', page)
        self.assertIn('id="population"', page)
        self.assertIn('0 eligible for scoring', page)

    def test_real_counts_and_percentages_replace_pending_values(self):
        rows, models = self.fixture(4)
        page = render_tables(rows, models)
        self.assertIn('annotation 4; detector-predicted 4', page)
        self.assertIn('4 eligible for scoring', page)
        self.assertIn('<td>12.50</td><td>25.00</td><td>75.00</td>', page)
        rows[0]['crop_class'] = '<script>'
        self.assertIn('&lt;script&gt;', table_rows(rows[:1]))

    def test_different_model_eligible_counts_are_rejected(self):
        rows, models = self.fixture(4)
        next(r for r in rows if r['model'] == 'trocr' and r['scoring_mode'] == 'normalised')['eligible'] = 2
        with self.assertRaisesRegex(ValueError, 'same eligible'):
            render_tables(rows, models)

    def test_provisional_values_have_separate_basis_and_real_subset_denominator(self):
        rows, models = self.fixture()
        provisional = [dict(r, score_basis='provisional_ai', candidate_crops=4,
                            eligible=None, cer=.125, wer=.25, exact_match=.75) for r in rows]
        page = render_tables(rows + provisional, models)
        self.assertEqual(page.count('<table>'), 3)
        self.assertIn('provisional agreement with AI-assisted labels', page)
        self.assertIn('of 10 available; AI-label subset', page)
        self.assertIn('<td>12.50</td><td>25.00</td><td>75.00</td>', page)
        self.assertIn('annotation 0; detector-predicted 0', page)
        self.assertTrue(all(r['cer'] is None for r in rows))


if __name__ == '__main__':
    unittest.main()
