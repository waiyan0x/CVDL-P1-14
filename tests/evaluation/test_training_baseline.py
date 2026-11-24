"""Training-split evaluation retains failed candidates and skips protected crops."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from backend.app.evaluation.review_decisions import digest
from scripts.freeze_automatic_ocr_layout import freeze
from scripts.score_ocr_training_split import diagnostic


class TrainingBaselineTests(unittest.TestCase):
    def test_raw_normalised_metrics_keep_failed_candidate_in_denominator(self):
        rows=[dict(review_id='T001',transcription='00A',label='front_eds_num'),
              dict(review_id='T002',transcription='X',label='front_eds_num')]
        predictions={'T001':dict(status='success',raw_text='00a'),
                     'T002':dict(status='error',raw_text='X')}
        summary,details=diagnostic(rows,predictions,'synthetic')
        raw=next(r for r in summary if r['field']=='all_fields_micro' and r['scoring_mode']=='raw')
        norm=next(r for r in summary if r['field']=='all_fields_micro' and r['scoring_mode']=='normalised')
        self.assertEqual((raw['candidate_crops'],raw['cer_pct'],raw['wer_pct'],raw['exact_match_pct']),(2,50,100,0))
        self.assertEqual((norm['cer_pct'],norm['wer_pct'],norm['exact_match_pct']),(25,50,50))
        self.assertEqual(norm['failed_or_missing'],1)
        self.assertTrue(all(r['hypothesis']=='' for r in details if r['review_id']=='T002'))

    def test_frozen_automatic_layout_preserves_policy_exclusion_without_fake_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);rgb=np.zeros((24,80,3),dtype=np.uint8);rgb[5:18,10:70]=255
            for name in ('one.png','two.png'):Image.fromarray(rgb).save(root/name)
            rows=[]
            for i,name in enumerate(('one.png','two.png'),1):
                rows.append(dict(review_id=f'T{i:04}',crop=name,image=f'{i}.jpg',label='front_eds_num',
                                 class_id='1',annotation_id=str(i),source_image_sha256=str(i)*64,
                                 crop_sha256=digest(root/name),box_xyxy='[0,0,80,24]',split='train',
                                 crop_width='80',crop_height='24',transcription='AB',legibility='full',
                                 field_status='present',exclusion_reason='Protected holdout' if i==2 else ''))
            review=root/'review.csv'
            with review.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            summary=freeze(review,root,'train',root/'frozen')
            self.assertEqual((summary['accepted'],summary['policy_excluded']),(1,1))
            entries=json.loads((root/'frozen/manifest.json').read_text())['entries']
            self.assertEqual({r['reviewer_type'] for r in entries},{'algorithm'})
            self.assertEqual(entries[1]['line_quads'],[])


if __name__=='__main__':
    unittest.main()
