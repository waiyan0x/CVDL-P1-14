import base64
import csv
import hashlib
import re
import shutil
import tempfile
from pathlib import Path
import unittest
import zipfile

from PIL import Image
from backend.app.evaluation.review_decisions import create_template, digest
from scripts.package_ocr_review import package
from tests.evaluation import test_crop_scoring


class PortableReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.crops = self.root / 'originals'
        self.crops.mkdir()
        self.output = self.root / 'review'
        for population, rid, split in (('training', 'T001', 'train'), ('validation', 'A001', 'valid')):
            crop = self.crops / f'{rid}.png'
            Image.new('RGB', (12, 8), 'white').save(crop)
            row = test_crop_scoring.CropScoringTests.row(
                self, rid=rid, text='PRIVATE_AI_TRANSCRIPTION', split=split,
                reviewer_type='AI', crop=f'{rid}.png', crop_local_path=str(crop),
                crop_sha256=digest(crop))
            path = self.workspace / f'{population}.source.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            create_template(path, self.workspace / f'{population}.decisions.template.csv')

    def prepare(self):
        return package(self.workspace, self.crops, self.output)

    def test_moved_bundle_has_embedded_images_and_no_ai_labels_or_human_attestations(self):
        audit = self.prepare()
        self.assertEqual(audit['embedded_images'], 2)
        for name, expected in audit['files_sha256'].items():
            self.assertEqual(digest(self.output / name), expected)
        with zipfile.ZipFile(self.output.with_suffix('.zip')) as archive:
            self.assertIsNone(archive.testzip())
            archive.extractall(self.root / 'moved')
        shutil.rmtree(self.crops)
        for population in ('training', 'validation'):
            moved = self.root / 'moved/review'
            html = (moved / f'{population}.html').read_text()
            self.assertNotIn('PRIVATE_AI_TRANSCRIPTION', html)
            self.assertNotIn(str(self.root), html)
            embedded = re.findall(r'src="data:image/png;base64,([^"]+)"', html)
            self.assertEqual(len(embedded), 1)
            image = next((moved / 'crops' / population).glob('*.png'))
            self.assertEqual(base64.b64decode(embedded[0]), image.read_bytes())
            self.assertFalse((moved / f'{population}.source.csv').exists())
            with (moved / f'{population}.decisions.template.csv').open(newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(all(not r['human_decision'] and not r['human_reviewer_type'] for r in rows))
            self.assertEqual(digest(moved / f'{population}.decisions.template.csv'),
                             digest(self.workspace / f'{population}.decisions.template.csv'))

    def test_nonblank_decision_and_changed_image_are_rejected(self):
        template = self.workspace / 'training.decisions.template.csv'
        before = template.read_text()
        with template.open(newline='') as handle:
            reader = csv.DictReader(handle)
            columns, rows = reader.fieldnames, list(reader)
        rows[0]['human_reviewer_type'] = 'human'
        with template.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'not blank'):
            self.prepare()
        self.assertFalse(self.output.exists())
        template.write_text(before)
        (self.crops / 'T001.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Crop hash/PNG mismatch'):
            self.prepare()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
