"""Lightweight acceptance checks; no recogniser model or TEST data is loaded."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT))
import common
from backend.app.evaluation.crop_scoring import normalise_text
from scripts.export_ocr_finetune_bundle import build,pairing,sha


class PreparationTests(unittest.TestCase):
    def test_early_stopping_plateau_counts_ties_and_keeps_best_epoch(self):
        stopping = common.CropCEREarlyStopping()
        decisions = [stopping.update(cer, epoch) for epoch, cer in enumerate([.3, .2, .21, .2, .22], 1)]
        self.assertEqual(decisions, [False, False, False, False, True])
        self.assertEqual(stopping.best_epoch, 2)
        self.assertEqual(stopping.best, .2)

    def test_early_stopping_improvement_resets_patience_and_rejects_nan(self):
        stopping = common.CropCEREarlyStopping()
        for epoch, cer in enumerate([.3, .3, .3, .2, .2, .2], 1):
            self.assertFalse(stopping.update(cer, epoch))
        self.assertTrue(stopping.update(.21, 7))
        self.assertEqual(stopping.best_epoch, 4)
        with self.assertRaises(ValueError):
            stopping.update(float('nan'), 8)

    def test_pairing_policy_preserves_punctuation_case_and_spaces(self):
        self.assertEqual(pairing('> A/B\nMixed case',1),(['> A/B Mixed case'],'two_text_lines_joined_for_one_region'))
        self.assertEqual(pairing('A\nB',2),(['A','B'],None))
        self.assertEqual(pairing('A',2),(None,'region_text_count_mismatch'))
        self.assertEqual(pairing('A',0),(None,'no_frozen_regions'))

    def test_normalisation_matches_repository(self):
        for s in ['CAFÉ.\nStraße 00B','> A / B','  097E  ','a\u00a0b','\u0130','E\u0301']:
            self.assertEqual(common.normalise_text(s),normalise_text(s))

    def test_crop_denominator_includes_missing_regions_and_line_cer_uses_only_pairs(self):
        refs=[dict(review_id='A',text='AB\nCD',line_count=2),dict(review_id='B',text='X',line_count=0)]
        lines=[dict(review_id='A',line_index=0,text='AB'),dict(review_id='A',line_index=1,text=None)]
        result=common.metrics(refs,lines,['ab','cd'])
        self.assertEqual(result['crop_count'],2);self.assertEqual(result['val_line_CER'],0)
        self.assertAlmostEqual(result['val_crop_CER'],1/6);self.assertEqual(result['val_crop_exact'],.5)

    def test_bundle_counts_hashes_pixels_and_overwrite_refusal(self):
        from PIL import Image
        import numpy as np
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bundle.zip';manifest=build(path)
            self.assertEqual(manifest['counts'],dict(train_crops=387,train_groups=129,train_pairs=366,
                              valid_crops=130,valid_pairs=124,valid_images=128,test_files=0))
            self.assertEqual(sum(r['split']=='train' for r in manifest['skipped']),24)
            self.assertEqual(sum(r['split']=='valid' for r in manifest['skipped']),6)
            before=sha(path)
            with self.assertRaises(FileExistsError):build(path)
            self.assertEqual(sha(path),before)
            with zipfile.ZipFile(path) as z:
                saved=json.loads(z.read('bundle_manifest.json'))
                for name,digest in saved['payload_sha256'].items():
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest)
                for sample in saved['equivalence_checks']:
                    with Image.open(io.BytesIO(z.read(sample['line']))) as im:array=np.asarray(im)
                    self.assertEqual(hashlib.sha256(array.tobytes()).hexdigest(),sample['pixel_sha256'])
                self.assertEqual(len({r['review_id'] for r in saved['equivalence_checks']}),5)
                self.assertFalse(any('test' in Path(n).parts for n in z.namelist()))

    def test_dictionary_coverage_or_explicit_failure(self):
        r=json.loads((HERE/'dictionary_check.json').read_text())
        for key in ['easyocr_missing','paddle_missing','trocr_missing']:self.assertEqual(r[key],[])
        with self.assertRaisesRegex(ValueError,"unsupported characters.*Z"):
            common.check_charset('AZ','A','synthetic dictionary')


if __name__=='__main__':unittest.main()
