"""Regression checks for the named sample manifest used by the app."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.app.errors import AppError
from backend.app.services.samples import SampleRegistry


class SampleRegistryTests(unittest.TestCase):
    def test_manifest_loads_nested_images_and_augmentation_with_descriptive_names(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'data/samples'
            folder.mkdir(parents=True)
            samples = []
            for category, name in [('Views', 'Side EDS'), ('Data augmentation', 'Rotation')]:
                path = folder / category / 'example.png'
                path.parent.mkdir()
                path.write_bytes(b'fixture')
                samples.append(dict(path=path.relative_to(root).as_posix(), category=category,
                                    subcategory=name, observation='Reviewed example.'))
            (folder / 'manifest.json').write_text(json.dumps(dict(samples=samples)), encoding='utf-8')
            registry = SampleRegistry(root)
            self.assertEqual([r['name'] for r in registry.list()], ['Side EDS', 'Rotation'])
            self.assertEqual(registry.path(1), (folder / 'Data augmentation/example.png').resolve())
            with self.assertRaises(AppError):
                registry.path(-1)

    def test_manifest_cannot_point_outside_samples(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'data/samples'
            folder.mkdir(parents=True)
            (folder / 'manifest.json').write_text(json.dumps(dict(samples=[dict(
                path='data/raw/photo.jpg', category='Views', subcategory='Side EDS',
                observation='Outside sample folder.')])), encoding='utf-8')
            with self.assertRaises(ValueError):
                SampleRegistry(root)

    def test_tracked_gallery_manifest_resolves_every_sample(self):
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads((root / 'data/samples/manifest.json').read_text(encoding='utf-8'))
        registry = SampleRegistry(root)
        expected = manifest['samples']
        self.assertEqual([r['name'] for r in registry.list()[:len(expected)]],
                         [r['subcategory'] for r in expected])
        for index, sample in enumerate(expected):
            self.assertEqual(registry.path(index), (root / sample['path']).resolve())


if __name__ == '__main__':
    unittest.main()
