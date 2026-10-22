"""Prepare an auditable, deduplicated validation view without changing source data."""
import hashlib
import json
from pathlib import Path
from PIL import Image

from backend.app.evaluation.provenance import file_hash, image_hashes, IMAGE_EXTENSIONS


def prepare_dataset(root: Path, output: Path) -> dict:
    training = image_hashes(root, 'train')
    seen, included, excluded = set(), [], []
    images, labels = output / 'images/test', output / 'labels/test'
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    for image in sorted((root / 'data/images/test').glob('*')):
        if not image.is_file() or image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        label = root / 'data/labels/test' / (image.stem + '.txt')
        digest = file_hash(image)
        reason = ('missing_labels' if not label.is_file() else
                  'training_overlap' if digest in training else
                  'duplicate_test_image' if digest in seen else None)
        item = {'image': str(image.relative_to(root)), 'sha256': digest}
        if reason:
            excluded.append({**item, 'reason': reason})
            continue
        prepared = images / image.name
        with Image.open(image) as decoded:
            # One bundled .jpg is AVIF internally. Make its encoding explicit so
            # Ultralytics cannot silently discard it as an unsupported JPEG.
            if decoded.format == 'AVIF':
                prepared = images / (image.stem + '.jpg')
                decoded.convert('RGB').save(prepared, format='JPEG', quality=95)
                item['prepared_encoding'] = 'JPEG transcoded from AVIF; pixels preserved, lossy JPEG'
                item['prepared_sha256'] = file_hash(prepared)
            else:
                decoded.verify()
                prepared.symlink_to(image.resolve())
        seen.add(digest)
        included.append({**item, 'label': str(label.relative_to(root)), 'label_sha256': file_hash(label)})
        (labels / label.name).symlink_to(label.resolve())
    if not included:
        raise ValueError('No labelled test images remain after overlap filtering.')
    fingerprint = hashlib.sha256(json.dumps(included, sort_keys=True).encode()).hexdigest()
    return {'id': 'bundled-bus-images', 'split': 'test-exact-train-overlap-excluded',
            'fingerprint_sha256': fingerprint, 'image_count': len(included),
            'included': included, 'excluded': excluded,
            'label_review': 'Bundled YOLO annotations; not independently re-annotated.'}
