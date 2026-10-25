"""Validate the package's offline image/box preparation with synthetic COCO data."""
import hashlib
import sys
from functools import partial
import json
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np
import torch
from torchvision import tv_tensors
from PIL import Image as PillowImage


class PreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'data/labelled/date'
        reference = self.root / 'docs/data_preparation/recipes/eds-torchvision-v1-reference.md'
        reference.parent.mkdir(parents=True)
        reference.write_text('Augmentation reference', encoding='utf-8')
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from data_preparation import images, splitting, datasets, augmentation, preprocessing
        from torch.utils.data import DataLoader
        self.scope = {'hashlib': hashlib, 'DataLoader': DataLoader}
        for module in (images, splitting, datasets, augmentation, preprocessing):
            self.scope.update({name: getattr(module, name) for name in dir(module)
                               if not name.startswith('_')})
        self.scope['build_augmented_dataset'] = partial(augmentation.build_augmented_dataset, root=self.root)
        torch.set_num_threads(2)
        cv2.setNumThreads(1)
        self.settings = dict(multiplier=3, brightness=.10, rotation_degrees=3.,
                             noise_fraction=.01, blur_radius=1.)
        for split, colour in zip(('train','val','test'), ((80,100,140),(140,90,60),(60,140,90))):
            folder = self.source / split
            folder.mkdir(parents=True)
            image = np.full((40,60,3),colour,dtype=np.uint8)
            cv2.rectangle(image,(12,8),(35,23),(255,255,255),-1)
            self.write_fixture(folder/f'{split}.png',image)
            images = [dict(id=1,file_name=f'{split}.png',width=60,height=40)]
            if split == 'train':
                self.write_fixture(folder/'negative.png',np.full((40,60,3),(20,30,40),dtype=np.uint8))
                images.append(dict(id=2,file_name='negative.png',width=60,height=40))
            data = dict(images=images,categories=[dict(id=1,name='eds')],
                        annotations=[dict(id=1,image_id=1,category_id=1,bbox=[12,8,24,16],area=384)])
            (folder/'_annotations.coco.json').write_text(json.dumps(data),encoding='utf-8')
        self.datasets = self.scope['load_coco_splits'](self.source)
        self.output = self.root/'data/training/date-aug-v1'

    def build(self, **kwargs):
        return self.scope['build_augmented_dataset'](self.datasets,self.output,self.settings,42,**kwargs)

    @staticmethod
    def write_fixture(path,rgb):
        ok,encoded = cv2.imencode('.png',cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if not ok:
            raise ValueError('Fixture encoding failed')
        encoded.tofile(path)

    def test_total_multiplier_and_untouched_holdouts(self):
        self.build()
        output = self.scope['load_coco_splits'](self.output)
        self.assertEqual(len(output['train']['rows']),6)
        for split in ('valid','test'):
            source = self.datasets[split]['folder']
            self.assertEqual((source/'_annotations.coco.json').read_bytes(),
                             (self.output/split/'_annotations.coco.json').read_bytes())
            for row in self.datasets[split]['rows']:
                self.assertEqual(row['path'].read_bytes(),
                                 (self.output/split/row['image']['file_name']).read_bytes())
        self.assertEqual(sum(not row['annotations'] for row in output['train']['rows']),3)
        self.assertEqual(len({row['image']['id'] for row in output['train']['rows']}),6)

    def test_rotation_boxes_enclose_actual_rotated_pixels(self):
        image = torch.zeros((3,70,100),dtype=torch.uint8)
        image[:,16:40,12:36] = 255
        settings = dict(self.settings,brightness=0,noise_fraction=0,blur_radius=0)
        rotated,annotations,_ = self.scope['augment_sample'](
            tv_tensors.Image(image),[dict(bbox=[12,16,24,24])],42,settings)
        box = annotations[0]['bbox']
        ys,xs = torch.where(rotated[0] > 250)
        x,y,w,h = box
        self.assertGreaterEqual(xs.min(),x-1)
        self.assertLessEqual(xs.max(),x+w+1)
        self.assertGreaterEqual(ys.min(),y-1)
        self.assertLessEqual(ys.max(),y+h+1)

    def test_negative_sample_stays_unlabelled(self):
        image, annotations, _ = self.scope['augment_sample'](
            tv_tensors.Image(torch.full((3,30,40),128,dtype=torch.uint8)),[],42,self.settings)
        self.assertEqual(annotations,[])
        self.assertGreaterEqual(image.shape[-1],40)
        self.assertGreaterEqual(image.shape[-2],30)

    def test_isolated_brightness_preview_changes_pixels_without_geometry(self):
        settings = dict(self.settings,rotation_degrees=0,noise_fraction=0,blur_radius=0)
        image = tv_tensors.Image(torch.full((3,20,30),100,dtype=torch.uint8))
        annotations = [dict(bbox=[4,5,10,7])]
        result, boxes, parameters = self.scope['augment_sample'](
            image,annotations,42,settings,parameters=dict(brightness=.9))
        self.assertEqual(tuple(result.shape),tuple(image.shape))
        self.assertTrue(torch.all(result == 90))
        self.assertEqual(boxes[0]['bbox'],annotations[0]['bbox'])
        self.assertEqual(parameters['brightness'],.9)
        with self.assertRaisesRegex(ValueError,'exceed configured'):
            self.scope['augment_sample'](image,annotations,42,settings,parameters=dict(brightness=.5))

    def test_repeat_is_identical_and_changes_are_rejected(self):
        manifest = self.build()
        self.assertEqual(manifest,self.build())
        self.settings['brightness'] = .05
        with self.assertRaisesRegex(ValueError,'Source/settings changed'):
            self.build()

    def test_modified_output_is_not_overwritten(self):
        manifest = self.build()
        name = next(name for name in manifest['checksums'] if name.endswith('.png'))
        (self.output/name).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Training dataset files changed'):
            self.build()

    def test_legacy_processed_path_cannot_receive_new_training_exports(self):
        self.output = self.root / 'data/processed/date/legacy'
        with self.assertRaisesRegex(ValueError, 'under data/training'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_general_documentation_edits_do_not_invalidate_frozen_recipe(self):
        manifest = self.build()
        guide = self.root / 'docs/data_preparation/README.md'
        guide.write_text('Updated navigation and directory layout', encoding='utf-8')
        self.assertEqual(manifest, self.build())

    def test_bad_box_is_rejected(self):
        path = self.source/'train/_annotations.coco.json'
        data = json.loads(path.read_text())
        data['annotations'][0]['bbox'] = [50,0,30,20]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Box outside image'):
            self.scope['load_coco_splits'](self.source)

    def test_marked_up_training_copy_is_excluded_without_removing_source(self):
        path = self.source/'train/_annotations.coco.json'
        data = json.loads(path.read_text())
        original = self.source/'train/train.png'
        marked = self.source/'train/annotated_train.png'
        marked.write_bytes(original.read_bytes())
        data['images'].append(dict(id=3,file_name=marked.name,width=60,height=40))
        data['annotations'].append(dict(id=2,image_id=3,category_id=1,bbox=[12,8,24,16]))
        path.write_text(json.dumps(data))
        self.datasets = self.scope['load_coco_splits'](self.source)
        manifest = self.build(excluded_prefixes=('annotated_',))
        self.assertEqual(manifest['excluded_train_images'],['annotated_train.png'])
        self.assertTrue(marked.exists())
        self.assertEqual(marked.read_bytes(),original.read_bytes())
        self.assertEqual(len(self.scope['load_coco_splits'](self.output)['train']['rows']),6)

    def test_letterbox_moves_boxes_and_preserves_aspect(self):
        image,boxes = self.scope['letterbox'](tv_tensors.Image(torch.zeros((3,40,80),dtype=torch.uint8)),[[10,10,20,10]],(160,160))
        self.assertEqual(tuple(image.shape[-2:]),(160,160))
        torch.testing.assert_close(boxes.as_subclass(torch.Tensor),torch.tensor([[20.,60.,40.,20.]]))

    def test_normalization_uses_training_only_and_float_chw(self):
        mean,std = self.scope['fit_training_statistics'](self.datasets['train'])
        self.write_fixture(self.datasets['valid']['rows'][0]['path'],np.zeros((40,60,3),dtype=np.uint8))
        next_mean,next_std = self.scope['fit_training_statistics'](self.datasets['train'])
        torch.testing.assert_close(mean,next_mean)
        torch.testing.assert_close(std,next_std)
        result = self.scope['model_input'](self.datasets['train']['rows'][0],(80,80),mean,std)
        self.assertEqual(result['image'].shape,(3,80,80))
        self.assertEqual(result['image'].dtype,torch.float32)
        self.assertTrue(torch.isfinite(result['image']).all())

    def test_group_shuffle_split_is_reproducible_and_keeps_groups(self):
        rows = []
        for i in range(30):
            digest = self.scope['hashlib'].sha256(str(i).encode()).hexdigest()
            rows.append(dict(source=f'{i}.png',aliases=[f'{i}.png'],pixel_hash=digest,
                             dhash=int(digest[:16],16)))
        rows[1]['dhash'] = rows[0]['dhash']
        splitter = self.scope['make_split_plan']
        ratios = dict(train=.7,valid=.2,test=.1)
        plan = splitter(rows,ratios,42)
        self.assertEqual(plan,splitter(rows,ratios,42))
        source_split = {row['source']:row['split'] for row in plan}
        self.assertEqual(source_split['0.png'],source_split['1.png'])
        for group in {row['group'] for row in plan}:
            self.assertEqual(len({row['split'] for row in plan if row['group']==group}),1)

    def test_dataset_and_loader_return_pytorch_detection_targets(self):
        dataset = self.scope['DetectionDataset'](self.datasets['train'],(80,80))
        loader = self.scope['DataLoader'](dataset,batch_size=2,collate_fn=self.scope['detection_collate'])
        images,targets = next(iter(loader))
        self.assertEqual(len(images),2)
        self.assertTrue(all(isinstance(image,torch.Tensor) for image in images))
        self.assertEqual(images[0].dtype,torch.float32)
        self.assertEqual(targets[0]['boxes'].shape,(1,4))
        self.assertEqual(targets[1]['boxes'].shape,(0,4))
        self.assertEqual(targets[0]['labels'].dtype,torch.int64)

    def test_avif_with_jpg_extension_uses_codec_fallback(self):
        path = self.root/'avif-content.jpg'
        PillowImage.new('RGB',(60,40),(80,100,140)).save(path,format='AVIF')
        image = self.scope['read_rgb'](path)
        self.assertIsInstance(image,tv_tensors.Image)
        self.assertEqual(tuple(image.shape),(3,40,60))
        self.assertEqual(image.dtype,torch.uint8)

    def test_raw_inventory_and_frozen_export_use_explicit_inputs(self):
        raw = self.root / 'data/raw/date'
        raw.mkdir(parents=True)
        self.write_fixture(raw/'original.png', np.full((20,30,3),80,dtype=np.uint8))
        (raw/'duplicate.png').write_bytes((raw/'original.png').read_bytes())
        (raw/'annotated_copy.png').write_bytes((raw/'original.png').read_bytes())
        generated = raw/'splits/previous/train'
        generated.mkdir(parents=True)
        (generated/'old.png').write_bytes((raw/'original.png').read_bytes())
        inventory, unique, excluded = self.scope['inspect_raw'](raw)
        self.assertEqual((len(inventory),len(unique),len(excluded)), (3,1,1))
        row = dict(unique[0], split='train', upload_name='frozen.png', group=0)
        destination = raw/'splits/new'
        settings = dict(raw=raw,inventory=inventory,seed=42,ratios=dict(train=.7,valid=.2,test=.1))
        self.scope['write_raw_split']([row],destination,**settings)
        self.scope['write_raw_split']([row],destination,**settings)
        self.assertEqual((destination/'train/frozen.png').read_bytes(),(raw/row['source']).read_bytes())
        with self.assertRaisesRegex(ValueError,'Frozen split changed'):
            self.scope['write_raw_split']([row],destination,**dict(settings,seed=43))
        with self.assertRaisesRegex(ValueError,'inside this raw cutoff'):
            self.scope['write_raw_split']([row],self.root/'outside',**settings)


if __name__ == '__main__':
    unittest.main()
