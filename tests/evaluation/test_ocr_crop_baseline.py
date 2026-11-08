"""Line layout, error retention, input integrity and timing-population contracts."""

import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from backend.app.evaluation.ocr_crop_baseline import load_crops, recognize_crop, segment_lines, summarize


ROOT = Path(__file__).resolve().parents[2]


def two_lines():
    rgb = np.zeros((40, 120, 3), dtype=np.uint8)
    rgb[4:13, 8:110] = 255
    rgb[24:34, 8:110] = 255
    return rgb


class ReaderStub:
    def __init__(self, fail_second=False):
        self.calls = []
        self.fail_second = fail_second

    def recognize(self, line, **kwargs):
        self.calls.append((line, kwargs))
        if self.fail_second and len(self.calls) == 2:
            raise RuntimeError("second line failed")
        return [(None, " Ab. " if len(self.calls) == 1 else "42", 0.8)]


class OCRCropBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "crop.png"
        Image.fromarray(two_lines()).save(self.path)
        self.record = {
            "review_id": "A001", "crop_set": "annotation", "field": "front_eds_destination",
            "crop_path": str(self.path), "crop_id": "crop.png", "input_width": 120, "input_height": 40,
            "crop_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
        }

    def test_multiline_partitions_cover_full_crop_in_order(self):
        for rgb in (two_lines(), 255-two_lines()):
            gray, regions, info = segment_lines(rgb)
            self.assertEqual(len(regions), 2)
            self.assertEqual(regions[0][1], 0)
            self.assertEqual(regions[-1][3], rgb.shape[0])
            self.assertEqual(regions[0][3], regions[1][1])
            self.assertTrue(info["needs_review"])
            reconstructed = np.vstack([gray[y1:y2, x1:x2] for x1,y1,x2,y2 in regions])
            np.testing.assert_array_equal(reconstructed, gray)

    def test_led_dot_row_gaps_do_not_create_fake_text_lines(self):
        rgb = np.zeros((32, 100, 3), dtype=np.uint8)
        rgb[8:12, 5:90] = 255
        rgb[13:17, 5:90] = 255
        _, regions, info = segment_lines(rgb)
        self.assertEqual(regions, [[0, 0, 100, 32]])
        self.assertEqual(info["status"], "single_band_unverified")

    def test_recognizes_each_line_and_preserves_engine_strings(self):
        reader = ReaderStub()
        result = recognize_crop(self.record, reader, lambda: None)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["line_count"], 2)
        self.assertEqual(result["raw_text"], " Ab. \n42")
        self.assertAlmostEqual(result["ocr_confidence"], 0.8)
        self.assertEqual(len(reader.calls), 2)
        self.assertTrue(all(call[1]["allowlist"] is None for call in reader.calls))

    def test_regular_seven_dot_rows_are_one_text_line(self):
        rgb = np.zeros((70, 120, 3), dtype=np.uint8)
        for y in range(3, 66, 9):
            rgb[y:y+5, 8:110] = (255, 210, 20)
        _, regions, info = segment_lines(rgb)
        self.assertEqual(len(regions), 1)
        self.assertEqual(info["foreground_mode"], "chromatic_led_support")

    def test_chromatic_lines_are_not_joined_by_gray_occluder(self):
        rgb = np.zeros((40, 120, 3), dtype=np.uint8)
        rgb[:, 1:18] = 180  # a gray obstruction spans both text rows
        rgb[4:13, 24:110] = (255, 210, 20)
        rgb[24:34, 24:110] = (255, 210, 20)
        _, regions, info = segment_lines(rgb)
        self.assertEqual(len(regions), 2)
        self.assertEqual(info["foreground_mode"], "chromatic_led_support")

    def test_no_contrast_is_explicit_error_without_full_crop_fallback(self):
        Image.fromarray(np.zeros((40, 120, 3), dtype=np.uint8)).save(self.path)
        self.record["crop_sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        reader = ReaderStub()
        result = recognize_crop(self.record, reader, lambda: None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["segmentation"]["status"], "no_contrast")
        self.assertFalse(reader.calls)

    def test_hash_mismatch_blocks_inference(self):
        self.record["crop_sha256"] = "0"*64
        reader = ReaderStub()
        result = recognize_crop(self.record, reader, lambda: None)
        self.assertEqual(result["status"], "error")
        self.assertIn("changed after preflight", result["error"])
        self.assertFalse(reader.calls)

    def test_failed_second_line_retains_partial_output_and_is_not_success(self):
        result = recognize_crop(self.record, ReaderStub(fail_second=True), lambda: None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["raw_text"], " Ab. ")
        self.assertIsNone(result["ocr_confidence"])
        self.assertEqual(result["line_count"], 2)
        self.assertEqual(len(result["line_regions"]), 2)

    def test_summary_excludes_fast_failures_from_latency_but_counts_them(self):
        success = recognize_crop(self.record, ReaderStub(), lambda: None)
        success.update(preprocessing_ms=2, recognition_ms=8, crop_total_ms=10)
        failed = dict(success, review_id="A002", status="error", recognition_ms=0.01)
        stats = next(r for r in summarize([success, failed]) if r["crop_set"] == "annotation" and r["field"] == "front_eds_destination")
        self.assertEqual((stats["attempted"], stats["completed"], stats["errors"]), (2, 1, 1))
        self.assertEqual(stats["recognition_ms_median"], 8)
        self.assertEqual(stats["recognition_ms_p95"], 8)

    def test_all_271_source_crops_are_loaded_without_training_or_label_fields(self):
        records = load_crops(ROOT / "evaluation/ocr_annotations/v4-reviewed-01")
        self.assertEqual(len(records), 271)
        self.assertEqual(sum(r["crop_set"] == "annotation" for r in records), 157)
        self.assertEqual(sum(r["crop_set"] == "prediction" for r in records), 114)
        for row in records:
            self.assertNotIn("transcription", row)
            self.assertNotIn("legibility", row)
            self.assertNotIn("group_id", row)


if __name__ == "__main__":
    unittest.main()
