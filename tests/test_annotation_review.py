"""Review decisions cannot silently approve empty predictions or alter drafts."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_preparation.annotation_review import ReviewProject, check_annotations
from data_preparation.review_cli import make_handler


class ReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "experiments/run"
        self.source = self.run / "data/labelled/2026-10-31"
        self.categories = dict(enumerate(("front_eds", "front_eds_num", "front_eds_route", "front_eds_destination")))
        for split in ("train", "val", "test"):
            folder = self.source / split
            folder.mkdir(parents=True)
            # The review core does not decode images; browser displays actual pixels.
            (folder / "sample.png").write_bytes(b"different pixels " + split.encode())
            coco = dict(images=[dict(id=1, file_name="sample.png", width=100, height=80, review_status="needs_review_empty")],
                        annotations=[], categories=[dict(id=k, name=v) for k, v in self.categories.items()])
            (folder / "_annotations.coco.json").write_text(json.dumps(coco))
        self.output = self.root / "data/labelled/2026-10-31"
        self.project = ReviewProject(self.run)

    def decision(self, status="accepted_negative", boxes=None):
        return dict(status=status, boxes=boxes or [], note="Checked the full image")

    def accept_all(self):
        for key in self.project.records:
            self.project.save(key, self.decision())

    def test_automatic_report_never_accepts_empty_predictions(self):
        report = self.project.write_report()
        self.assertEqual(report["summary"]["statuses"], {"needs_review": 3})
        self.assertTrue(all(r["candidate"] == "unknown_empty" for r in report["rows"]))
        self.assertTrue(all(r["automatic_issues"] for r in report["rows"]))
        with self.assertRaisesRegex(ValueError, "3 still pending"):
            self.project.export(self.output, root=self.root)
        self.assertFalse(self.output.exists())

    def test_positive_needs_panel_and_negative_needs_zero_boxes(self):
        content = [dict(category_id=1, bbox=[10, 10, 20, 10])]
        with self.assertRaisesRegex(ValueError, "panel box"):
            self.project.save("train/1", self.decision("accepted_positive", content))
        panel = [dict(category_id=0, bbox=[10, 10, 20, 10])]
        with self.assertRaisesRegex(ValueError, "zero boxes"):
            self.project.save("train/1", self.decision("accepted_negative", panel))
        self.project.save("train/1", self.decision("accepted_positive", panel))
        self.assertEqual(self.project.report()["summary"]["statuses"]["accepted_positive"], 1)

    def test_bad_boxes_are_rejected(self):
        for bbox in ([0, 0, 0, 3], [-1, 0, 2, 3], [99, 0, 3, 3], [0, 0, float("nan"), 3]):
            with self.subTest(bbox=bbox), self.assertRaises(ValueError):
                self.project.save("train/1", self.decision("accepted_positive", [dict(category_id=0, bbox=bbox)]))

    def test_automatic_checks_flag_content_containment_and_duplicates(self):
        boxes = [dict(category_id=0, bbox=[0, 0, 20, 20]),
                 dict(category_id=1, bbox=[30, 30, 5, 5]),
                 dict(category_id=1, bbox=[30, 30, 5, 5])]
        issues = check_annotations(boxes, dict(width=100, height=80), self.categories)
        self.assertTrue(any("not contained" in i for i in issues))
        self.assertTrue(any("duplicate" in i for i in issues))

    def test_decisions_persist_without_changing_draft_coco(self):
        path = self.source / "train/_annotations.coco.json"
        before = path.read_bytes()
        self.project.save("train/1", self.decision())
        restored = ReviewProject(self.run)
        self.assertEqual(restored.decisions, self.project.decisions)
        self.assertEqual(path.read_bytes(), before)

    def test_source_changes_invalidate_review_and_export(self):
        self.accept_all()
        (self.source / "train/sample.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Draft files changed"):
            ReviewProject(self.run)
        with self.assertRaisesRegex(ValueError, "Draft files changed"):
            self.project.export(self.output, root=self.root)

    def test_export_preserves_membership_and_writes_accepted_boxes_and_manifest(self):
        self.accept_all()
        boxes = [dict(category_id=0, bbox=[10, 10, 30, 20]), dict(category_id=1, bbox=[15, 15, 10, 10])]
        self.project.save("train/1", self.decision("accepted_positive", boxes))
        self.project.export(self.output, root=self.root)
        for split in ("train", "val", "test"):
            data = json.loads((self.output / split / "_annotations.coco.json").read_text())
            self.assertEqual(data["images"][0]["review_status"], "accepted")
            self.assertEqual(data["images"][0]["null_declared"], split != "train")
            self.assertEqual(len(data["annotations"]), 2 if split == "train" else 0)
            self.assertEqual((self.output / split / "sample.png").read_bytes(), (self.source / split / "sample.png").read_bytes())
        manifest = json.loads((self.output / "preparation_manifest.json").read_text())
        for name, checksum in manifest["checksums"].items():
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), checksum)
        with self.assertRaises(FileExistsError):
            self.project.export(self.output, root=self.root)

    def test_export_cannot_escape_labelled_root(self):
        self.accept_all()
        with self.assertRaisesRegex(ValueError, "under data/labelled"):
            self.project.export(self.root / "other", root=self.root)

    def test_image_path_traversal_is_rejected(self):
        path = self.source / "train/_annotations.coco.json"
        data = json.loads(path.read_text())
        data["images"][0]["file_name"] = "../outside.png"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "outside split"):
            ReviewProject(self.run)

    def test_mask_annotations_cannot_be_silently_exported_as_boxes(self):
        path = self.source / "train/_annotations.coco.json"
        data = json.loads(path.read_text())
        data["annotations"] = [dict(id=1, image_id=1, category_id=0, bbox=[0, 0, 10, 10],
                                    segmentation=[[0, 0, 10, 0, 10, 10]])]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "not masks"):
            ReviewProject(self.run)

    def test_cli_report_runs_without_third_party_dependencies(self):
        script = Path(__file__).resolve().parents[1] / "scripts/review_annotations.py"
        result = subprocess.run([sys.executable, "-S", str(script), "--run-dir", str(self.run)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.run / "automatic_review.json").is_file())

    def test_local_api_requires_token_and_persists_decisions(self):
        server = HTTPServer(("127.0.0.1", 0), make_handler(self.project, "test-token"))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(server.shutdown)
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        self.addCleanup(client.close)
        client.request("GET", "/data")
        response = client.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        client.request("GET", "/?token=test-token")
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"Accept positive", response.read())
        body = dict(self.decision(), key="train/1")
        client.request("POST", "/decision?token=test-token", json.dumps(body), {"Content-Type": "application/json"})
        response = client.getresponse()
        self.assertEqual(response.status, 200, response.read())
        self.assertEqual(ReviewProject(self.run).decisions["train/1"]["status"], "accepted_negative")
        client.request("POST", "/decision?token=test-token", json.dumps(body),
                       {"Content-Type": "application/json", "Origin": "https://unrelated.example"})
        response = client.getresponse()
        self.assertEqual(response.status, 403)
        response.read()


if __name__ == "__main__":
    unittest.main()
