import tempfile
import unittest
import json
import csv
import sys
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageDraw

from backend.app.evaluation.seven_segment_baselines import (
    EasyOCRBaseline, TemplateBaseline, TesseractBaseline,
)
from backend.app.evaluation.seven_segment_dataset import build_manifest, INPUT_COLUMNS, write_manifest
from scripts.seven_segment_baseline import run


class SevenSegmentBaselineTests(unittest.TestCase):
    def test_template_baseline_reads_two_synthetic_glyphs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one = Image.new("L", (16, 32), 0)
            draw = ImageDraw.Draw(one)
            draw.rectangle((11, 3, 13, 28), fill=255)
            two = Image.new("L", (16, 32), 0)
            draw = ImageDraw.Draw(two)
            draw.rectangle((2, 3, 13, 5), fill=255)
            draw.rectangle((11, 5, 13, 16), fill=255)
            draw.rectangle((2, 16, 13, 18), fill=255)
            draw.rectangle((2, 18, 4, 28), fill=255)
            draw.rectangle((2, 28, 13, 30), fill=255)
            one.save(root / "1.png")
            two.save(root / "2.png")
            crop = Image.new("L", (44, 32), 0)
            crop.paste(one, (1, 0))
            crop.paste(two, (25, 0))
            (root / "crops").mkdir()
            crop_path = root / "crops/reading.png"
            crop.save(crop_path)
            text, confidence = TemplateBaseline(root).predict(crop_path)
            self.assertEqual(text, "12")
            self.assertGreater(confidence, .9)

    def test_template_provenance_rejects_validation_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("L", (4, 4), 255).save(root / "1.png")
            (root / "templates.json").write_text(json.dumps([
                {"glyph": "1", "file": "1.png", "source_sample_id": "heldout-1"}]))
            with self.assertRaisesRegex(ValueError, "not sourced from training"):
                TemplateBaseline(root, training_sample_ids={"train-1"})

    def test_runner_writes_scored_csv_for_reviewed_crop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crops = root / "crops"
            templates = root / "templates"
            crops.mkdir()
            templates.mkdir()
            inventory = root / "inventory.csv"
            with inventory.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=INPUT_COLUMNS)
                writer.writeheader()
                for index in range(3):
                    image = Image.new("L", (12, 24), 0)
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((7, 3, 9, 19), fill=255)
                    image.putpixel((0, 0), index * 10)  # distinct crop hashes
                    image.save(crops / f"{index}.png")
                    writer.writerow({"sample_id": f"sample-{index}", "crop_path": f"crops/{index}.png",
                                     "display_group_id": f"display-{index}",
                                     "recording_id": f"recording-{index}", "frame_index": index,
                                     "field_name": "voltage", "truth_raw": "1",
                                     "label_status": "readable", "primary_reviewer": "A",
                                     "secondary_reviewer": "B", "augmented_from": ""})
            manifest = build_manifest(inventory, dataset_id="synthetic-test", version="v1")
            train_id = next(row["sample_id"] for row in manifest["samples"] if row["split"] == "train")
            template = Image.new("L", (12, 24), 0)
            ImageDraw.Draw(template).rectangle((7, 3, 9, 19), fill=255)
            template.save(templates / "1.png")
            (templates / "templates.json").write_text(json.dumps([
                {"glyph": "1", "file": "1.png", "source_sample_id": train_id}]))
            manifest_path = root / "manifest.json"
            write_manifest(manifest, manifest_path)
            output = root / "results.csv"
            summary = run(manifest_path, engine="template", split="val", run_id="test-v1",
                          output=output, templates=templates, warmup_runs=1, timed_runs=2)
            self.assertEqual(summary["samples"], 1)
            with output.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["prediction_raw"], "1")
            self.assertEqual(rows[0]["strict_match"], "true")
            self.assertEqual(rows[0]["device"], "cpu")

    def test_tesseract_tsv_keeps_one_reading_and_weighted_score(self):
        tsv = "level\ttext\tconf\n5\t1\t80\n5\t23\t90\n"
        with patch("backend.app.evaluation.seven_segment_baselines.shutil.which", return_value="tesseract"), \
             patch("backend.app.evaluation.seven_segment_baselines.subprocess.run",
                   return_value=SimpleNamespace(stdout=tsv)):
            text, confidence = TesseractBaseline().predict(Path("unused.png"))
        self.assertEqual(text, "123")
        self.assertAlmostEqual(confidence, (80 + 2 * 90) / 300)

    def test_easyocr_crop_uses_single_reading_allowlist(self):
        calls = []

        class FakeReader:
            def __init__(self, languages, **kwargs):
                calls.append(kwargs)

            def recognize(self, image, **kwargs):
                calls.append(kwargs)
                return [([0, 0, 12, 24], "1.2", .8)]

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "crop.png"
            Image.new("RGB", (12, 24), "black").save(image_path)
            with patch.dict(sys.modules, {"easyocr": SimpleNamespace(Reader=FakeReader)}):
                text, confidence = EasyOCRBaseline(device="mps").predict(image_path)
        self.assertEqual(text, "1.2")
        self.assertAlmostEqual(confidence, .8)
        self.assertEqual(calls[0]["gpu"], "mps")
        self.assertEqual(calls[1]["allowlist"], "0123456789.+-")


if __name__ == "__main__":
    unittest.main()
