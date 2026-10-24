"""Presentation samples and original project test images, with stable registry IDs."""
from ..errors import AppError

PRESENTATION = [('01-daylight-329.jpg', 'Daylight'), ('02-night-965.jpg', 'Night, wet glass'),
                ('03-angle-181.jpg', 'Angled, double deck'), ('04-stop-133.jpg', 'At stop, partial view')]
PREFERRED = ['ea005707__9aebe21b-3.jpg', 'fce01393-3b0671f0-272.jpg',
             '49775ed2__a5dcfafd-122.jpg', '0c7ddfa8-27d65774-133.jpg']


class SampleRegistry:
    def __init__(self, root):
        self.entries = []
        for name, description in PRESENTATION:
            path = root / 'data/samples' / name
            if path.is_file():
                self.entries.append((path, f'Sample {len(self.entries) + 1}', description))
        originals = sorted((root / 'data/images/test').glob('*.jpg'),
                           key=lambda path: (PREFERRED.index(path.name) if path.name in PREFERRED else 99, path.name))
        for index, path in enumerate(originals, 1):
            if not path.name.startswith('annotated_'):
                self.entries.append((path, f'Project photo {index:02}', 'Original project dataset'))

    def list(self):
        return [{'id': index, 'name': name, 'description': description,
                 'url': f'/api/samples/{index}/image', 'source': path.name}
                for index, (path, name, description) in enumerate(self.entries)]

    def path(self, identity):
        if identity < 0 or identity >= len(self.entries):
            raise AppError(404, 'sample_not_found', 'Sample not found.')
        return self.entries[identity][0]
