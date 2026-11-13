"""Synthetic deliverable and Paddle adapter checks, without Paddle or downloads."""

import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from backend.app.evaluation.paddle_crop_reader import PaddleCropReader
from scripts.prepare_ocr_baseline_deliverable import prepare, timestamp
from scripts.fetch_paddle_baseline import fetch, FILES
from tests.evaluation import test_crop_scoring


class BaselineDeliverableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/"source"
        (self.source/"crops").mkdir(parents=True)
        crop = self.source/"crops/A001.png"
        Image.new("RGB",(80,20)).save(crop)
        self.row = test_crop_scoring.CropScoringTests.row(self, reviewer_type="AI",crop_sha256=hashlib.sha256(crop.read_bytes()).hexdigest())
        self.review = self.root/"review.csv"
        with self.review.open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=list(self.row));writer.writeheader();writer.writerow(self.row)
        self.layout = self.root/"manifest.json"
        self.layout.write_text(json.dumps({"independent_human_review":False,"entries":[{
            "review_id":"A001","crop_id":self.row["crop"],"crop_sha256":self.row["crop_sha256"],
            "input_width":80,"input_height":20,"field":"front_eds_destination",
            "line_quads":[],"review_status":"needs_resolution","line_count":0}]}))
        self.layout.with_suffix(".sha256").write_text(hashlib.sha256(self.layout.read_bytes()).hexdigest()+"  manifest.json\n")
        self.config = self.root/"config.json"
        self.config.write_text(json.dumps({"models":[{"id":x} for x in ["easyocr","trocr","paddleocr"]]}))
        self.output=self.root/"output"

    def prepare(self):
        return prepare([self.review],self.config,self.layout,self.source,self.output)

    def test_bundle_counts_unknowns_and_keeps_human_decisions_blank(self):
        audit=self.prepare()
        self.assertEqual(audit["validation_crops"],1)
        self.assertEqual(audit["eligible"],0)
        self.assertEqual(audit["view_counts"],{"unknown":1})
        self.assertFalse(audit["reserved_test_accessed"])
        html=(self.output/"baseline_tables.html").read_text()
        self.assertEqual(html.count("<table>"),3)
        with (self.output/"human_decisions_1.csv").open(newline="") as handle:
            row=next(csv.DictReader(handle))
            self.assertEqual(row["human_decision"],"")
            self.assertEqual(row["human_reviewer"],"")
        with self.assertRaises(FileExistsError): self.prepare()

    def test_invalid_hash_or_reserved_test_never_publishes(self):
        (self.source/"crops/A001.png").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.output.exists())
        self.row["split"]="test"
        with self.review.open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=list(self.row));writer.writeheader();writer.writerow(self.row)
        with self.assertRaisesRegex(ValueError,"validation only"): self.prepare()

    def test_timestamp_candidates_are_conservative_and_validate_dates(self):
        self.assertEqual(timestamp("20261105_153012.jpg"),"2026-11-05T15:30:12")
        self.assertEqual(timestamp("2026-11-05 15.30.12.jpg"),"2026-11-05T15:30:12")
        self.assertEqual(timestamp("20260230_153012.jpg"),"")
        self.assertEqual(timestamp("bus_145.rf.123abc.jpg"),"")


class PaddleAdapterTests(unittest.TestCase):
    def test_native_line_prediction_and_empty_text(self):
        seen=[]
        def predict(**kwargs):
            seen.append(kwargs)
            return iter([{"rec_text":"00B","rec_score":.75}])
        result=PaddleCropReader(SimpleNamespace(predict=predict)).recognize(np.zeros((10,40),dtype=np.uint8))
        self.assertEqual(result,[(None,"00B",.75)])
        self.assertEqual(seen[0]["input"].shape,(10,40,3))
        self.assertEqual(seen[0]["batch_size"],1)

    def test_ambiguous_output_count_and_bad_text_fail(self):
        for outputs in [[],[{"rec_text":"A","rec_score":.5}]*2,[{"rec_text":None,"rec_score":.5}]]:
            model=SimpleNamespace(predict=lambda **kwargs: iter(outputs))
            with self.assertRaises(ValueError):
                PaddleCropReader(model).recognize(np.zeros((10,40),dtype=np.uint8))

    def test_downloader_pins_revision_records_hashes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"model"
            metadata={"sha":"a"*40,"siblings":[{"rfilename":f} for f in FILES]}
            responses=[json.dumps(metadata).encode(), b"graph", b"weights", b"configuration"]
            urls=[]
            def open_url(url,**kwargs):
                urls.append(url)
                return io.BytesIO(responses.pop(0))
            with patch("scripts.fetch_paddle_baseline.urllib.request.urlopen",side_effect=open_url):
                self.assertEqual(fetch(output),"a"*40)
            self.assertTrue(all('/resolve/'+"a"*40+'/' in u for u in urls[1:]))
            provenance=json.loads((output/"provenance.json").read_text())
            self.assertEqual(provenance["files_sha256"]["inference.pdiparams"],hashlib.sha256(b"weights").hexdigest())
            with self.assertRaises(FileExistsError): fetch(output)


if __name__ == "__main__":
    unittest.main()
