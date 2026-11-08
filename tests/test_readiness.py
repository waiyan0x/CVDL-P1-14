"""Regression checks for reviewed leakage removal and frozen holdouts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_preparation.datasets import load_coco_splits
from data_preparation.images import file_hash
from data_preparation.readiness import CLASS_ORDER, audit_labels, clean_labels


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source, self.output = self.root / "accepted", self.root / "clean"
        for index, split in enumerate(("train", "val", "test")):
            folder = self.source / split
            folder.mkdir(parents=True)
            pixels = np.random.default_rng(index).integers(0, 256, (80, 100, 3), dtype=np.uint8)
            Image.fromarray(pixels).save(folder / "scene.png")
            coco = dict(images=[dict(id=1, file_name="scene.png", width=100, height=80)],
                        annotations=[], categories=[dict(id=i+1, name=n) for i, n in enumerate(CLASS_ORDER)])
            (folder / "_annotations.coco.json").write_text(json.dumps(coco), encoding="utf-8")
        # Same scene re-encoded with different pixels: near-duplicate, not exact.
        with Image.open(self.source / "val/scene.png") as image:
            image.save(self.source / "train/copy.jpg", quality=95)
        path = self.source / "train/_annotations.coco.json"
        coco = json.loads(path.read_text())
        coco["images"].append(dict(id=2, file_name="copy.jpg", width=100, height=80))
        path.write_text(json.dumps(coco), encoding="utf-8")
        self.datasets = load_coco_splits(self.source)
        self.decisions = dict(exclude_train=[dict(file_name="copy.jpg",
            sha256=file_hash(self.source / "train/copy.jpg"), matches_split="valid",
            matches_file_name="scene.png", matches_sha256=file_hash(self.source / "val/scene.png"))])

    def test_cleaning_removes_overlap_and_preserves_holdouts(self):
        self.assertFalse(audit_labels(self.datasets)["automated_checks_passed"])
        manifest = clean_labels(self.datasets, self.output, self.decisions)
        self.assertTrue(manifest["audit"]["automated_checks_passed"])
        self.assertFalse((self.output / "train/copy.jpg").exists())
        self.assertTrue((self.source / "train/copy.jpg").exists())
        for split in ("val", "test"):
            for source in (self.source / split).iterdir():
                self.assertEqual(source.read_bytes(), (self.output / split / source.name).read_bytes())
        self.assertEqual(manifest, clean_labels(self.datasets, self.output, self.decisions))

    def test_changed_review_evidence_is_rejected(self):
        self.decisions["exclude_train"][0]["matches_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "counterpart"):
            clean_labels(self.datasets, self.output, self.decisions)
        self.assertFalse(self.output.exists())

    def test_modified_export_is_not_overwritten(self):
        clean_labels(self.datasets, self.output, self.decisions)
        (self.output / "val/scene.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "output changed"):
            clean_labels(self.datasets, self.output, self.decisions)

    def test_unresolved_leakage_cannot_be_exported(self):
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            clean_labels(self.datasets, self.output, dict(exclude_train=[]))

    def test_exact_duplicate_can_be_audited_and_cleaned_but_not_trained(self):
        copy = self.source / 'train/copy.jpg'
        copy.write_bytes((self.source / 'val/scene.png').read_bytes())
        self.decisions['exclude_train'][0]['sha256'] = file_hash(copy)
        with self.assertRaisesRegex(ValueError,'Exact image duplicated'):
            load_coco_splits(self.source)
        datasets = load_coco_splits(self.source,allow_cross_split_duplicates=True)
        self.assertFalse(audit_labels(datasets)['automated_checks_passed'])
        clean_labels(datasets,self.output,self.decisions)
        self.assertTrue(audit_labels(load_coco_splits(self.output))['automated_checks_passed'])

    def test_excluded_annotations_do_not_block_cleaned_preflight(self):
        # A legacy class used only by the reviewed excluded copy must not survive.
        for folder in self.source.iterdir():
            path = folder / '_annotations.coco.json'
            coco = json.loads(path.read_text())
            coco['categories'].append(dict(id=99,name='legacy_markup'))
            if folder.name == 'train':
                coco['annotations'].append(dict(id=1,image_id=2,category_id=99,bbox=[10,10,20,20]))
            path.write_text(json.dumps(coco),encoding='utf-8')
        datasets = load_coco_splits(self.source)
        self.assertFalse(audit_labels(datasets)['automated_checks_passed'])
        result = clean_labels(datasets,self.output,self.decisions)
        self.assertTrue(result['audit']['automated_checks_passed'])
        self.assertEqual(result['audit']['splits'][0]['boxes'],0)


if __name__ == "__main__":
    unittest.main()
