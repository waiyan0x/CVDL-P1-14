"""Frozen geometry integrity, full coverage and explicit no-fallback contracts."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from backend.app.evaluation.ocr_crop_baseline import load_crops, recognize_crop
from backend.app.evaluation.ocr_line_layout import extract_region, line_quads, load_layout, validate_entry
from scripts.freeze_ocr_line_layout import freeze


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "evaluation/ocr_annotations/v4-reviewed-01"
LAYOUT = ROOT / "evaluation/ocr_layouts/v4-lines-v1/manifest.json"


class ReaderStub:
    def __init__(self):
        self.calls = []

    def recognize(self, image, **kwargs):
        self.calls.append(image.shape)
        return [(None, "example", 0.5)]


class OCRLineLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_crops(WORKSPACE)
        cls.manifest, cls.entries = load_layout(LAYOUT, cls.records)
        cls.by_id = {r["review_id"]: r for r in cls.records}

    def test_complete_coverage_and_honest_review_attribution(self):
        self.assertEqual(len(self.entries), 271)
        self.assertEqual(self.manifest["summary"]["accepted"], 251)
        self.assertEqual(self.manifest["summary"]["unresolved"], 20)
        self.assertEqual(self.manifest["summary"]["line_regions"], 280)
        for entry in self.entries.values():
            self.assertEqual(entry["reviewer_type"], "AI")
            self.assertFalse(entry["independent_human_review"])

    def test_horizontal_bands_are_exact_slices_with_no_lost_pixels(self):
        image = np.arange(40*100, dtype=np.uint16).reshape(40, 100)
        regions = line_quads(100, 40, [[13, 13], [25, 25]])
        patches = [extract_region(image, quad) for quad in regions]
        np.testing.assert_array_equal(np.vstack(patches), image)

    def test_sloping_partitions_cover_the_source_geometrically(self):
        for entry in self.entries.values():
            if entry["review_status"] != "accepted":
                self.assertFalse(entry["line_quads"])
                continue
            area = 0
            for quad in entry["line_quads"]:
                left = quad[3][1]-quad[0][1]
                right = quad[2][1]-quad[1][1]
                area += entry["input_width"]*(left+right)/2
            self.assertEqual(area, entry["input_width"]*entry["input_height"])

    def test_rejects_outside_crossing_unordered_and_thin_boundaries(self):
        for separators in ([[0, 10]], [[10, 40]], [[-2, 10]], [[20, 20], [10, 30]], [[10, 10], [11, 20]], [[10.5, 10]]):
            with self.subTest(separators=separators), self.assertRaises(ValueError):
                line_quads(100, 40, separators)

    def test_sloping_regions_have_fixed_documented_raster_shape(self):
        image = np.tile(np.arange(40, dtype=np.uint8)[:, None], (1, 100))
        quads = line_quads(100, 40, [[12, 18]])
        self.assertEqual(extract_region(image, quads[0]).shape, (18, 100))
        self.assertEqual(extract_region(image, quads[1]).shape, (28, 100))

    def test_unresolved_crop_never_uses_automatic_or_full_crop_fallback(self):
        reader = ReaderStub()
        with patch("backend.app.evaluation.ocr_crop_baseline.segment_lines", side_effect=AssertionError("automatic fallback forbidden")):
            result = recognize_crop(self.by_id["A002"], reader, lambda: None, self.entries["A002"])
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["segmentation"]["status"], "fixed_layout_unresolved")
        self.assertFalse(reader.calls)
        self.assertEqual(result["line_count"], 0)
        self.assertIsNone(result["ocr_confidence"])

    def test_fixed_multiline_geometry_replaces_automatic_candidate(self):
        reader = ReaderStub()
        with patch("backend.app.evaluation.ocr_crop_baseline.segment_lines", side_effect=AssertionError("automatic fallback forbidden")):
            result = recognize_crop(self.by_id["A003"], reader, lambda: None, self.entries["A003"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(reader.calls), 2)
        self.assertEqual(result["raw_text"], "example\nexample")
        self.assertEqual(result["line_quads"], self.entries["A003"]["line_quads"])

    def test_crop_identity_and_geometry_cannot_be_silently_changed(self):
        entry = copy.deepcopy(self.entries["A003"])
        entry["crop_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "crop_sha256 mismatch"):
            validate_entry(entry, self.by_id["A003"])
        entry = copy.deepcopy(self.entries["A003"])
        entry["line_quads"][0][2][1] += 1
        with self.assertRaisesRegex(ValueError, "quadrilaterals"):
            validate_entry(entry, self.by_id["A003"])

    def test_tampered_frozen_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_bytes(LAYOUT.read_bytes()+b" ")
            path.with_suffix(".sha256").write_bytes(LAYOUT.with_suffix(".sha256").read_bytes())
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_layout(path, self.records)

    def test_existing_version_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "manifest.json"
            marker.write_text("existing frozen review")
            with self.assertRaises(FileExistsError):
                freeze(WORKSPACE, output / "missing.json", output, output, "v1")
            self.assertEqual(marker.read_text(), "existing frozen review")


if __name__ == "__main__":
    unittest.main()
