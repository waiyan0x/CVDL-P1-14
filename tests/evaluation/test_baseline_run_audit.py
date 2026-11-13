import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("baseline_run_audit", Path(__file__).resolve().parents[2] / "scripts/audit_ocr_baseline_runs.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BaselineRunAuditTests(unittest.TestCase):
    def test_unresolved_layout_cannot_be_replaced_by_success_or_fallback(self):
        entry = dict(review_id="A001", input_width=10, input_height=5,
                     line_quads=[], line_count=0, review_status="unresolved")
        prediction = dict(entry, status="error", raw_text="", line_outputs=[],
                          error="unresolved", line_regions=[])
        module.check_prediction(prediction, entry)
        for change in (dict(status="success"), dict(raw_text="guessed"), dict(error=None)):
            with self.assertRaises(ValueError):
                module.check_prediction(dict(prediction, **change), entry)

    def test_line_order_dimensions_and_retained_model_errors(self):
        quad = [[0, 0], [10, 0], [10, 5], [0, 5]]
        entry = dict(review_id="P001", input_width=10, input_height=5,
                     line_quads=[quad], line_count=1, review_status="accepted")
        prediction = dict(entry, status="success", raw_text="ABC", error=None,
                          line_regions=[[0, 0, 10, 5]], line_outputs=[dict(
                              index=0, quad_xy=quad, box_xyxy=[0, 0, 10, 5], line_input_size=[10, 5])])
        module.check_prediction(prediction, entry)
        changed = copy.deepcopy(prediction)
        changed["line_outputs"][0]["line_input_size"] = [5, 10]
        with self.assertRaisesRegex(ValueError, "size/order"):
            module.check_prediction(changed, entry)
        with self.assertRaisesRegex(ValueError, "Missing successful"):
            module.check_prediction(dict(prediction, line_outputs=[]), entry)
        # An engine failure before producing a line remains a valid recorded attempt.
        module.check_prediction(dict(prediction, status="error", error="token limit",
                                     raw_text="", line_outputs=[]), entry)


if __name__ == "__main__":
    unittest.main()
