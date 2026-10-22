from pathlib import Path
from PIL import Image

from scripts.detection_dataset import prepare_dataset


def add(root, split, name, content, labelled=True):
    image = root / 'data/images' / split / f'{name}.jpg'
    image.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (16, 16), color=(content[0], content[-1], len(content))).save(image)
    if labelled:
        label = root / 'data/labels' / split / f'{name}.txt'
        label.parent.mkdir(parents=True, exist_ok=True)
        label.write_text('1 .5 .5 .2 .2\n')
    return image


def test_dataset_excludes_train_overlap_and_unlabelled_files(tmp_path):
    add(tmp_path, 'train', 'training', b'same')
    add(tmp_path, 'test', 'overlap', b'same')
    original = add(tmp_path, 'test', 'valid', b'unseen')
    add(tmp_path, 'test', 'annotated', b'drawing', labelled=False)
    report = prepare_dataset(tmp_path, tmp_path / 'prepared')
    assert len(report['included']) == 1
    assert report['included'][0]['image'] == 'data/images/test/valid.jpg'
    assert {row['reason'] for row in report['excluded']} == {'training_overlap', 'missing_labels'}
    with Image.open(original) as decoded:
        assert decoded.size == (16, 16)
    assert (tmp_path / 'prepared/images/test/valid.jpg').resolve() == original


def test_dataset_deduplicates_test_content_and_has_stable_fingerprint(tmp_path):
    add(tmp_path, 'test', 'a', b'unseen')
    add(tmp_path, 'test', 'b', b'unseen')
    first = prepare_dataset(tmp_path, tmp_path / 'one')
    second = prepare_dataset(tmp_path, tmp_path / 'two')
    assert len(first['included']) == 1
    assert first['excluded'][0]['reason'] == 'duplicate_test_image'
    assert first['fingerprint_sha256'] == second['fingerprint_sha256']


def test_avif_misnamed_as_jpeg_is_transcoded_and_recorded(tmp_path):
    original = add(tmp_path, 'test', 'avif', b'new')
    Image.new('RGB', (16, 16), 'white').save(original, format='AVIF')
    report = prepare_dataset(tmp_path, tmp_path / 'prepared')
    entry = report['included'][0]
    assert entry['prepared_encoding'].startswith('JPEG transcoded from AVIF')
    with Image.open(tmp_path / 'prepared/images/test/avif.jpg') as decoded:
        assert decoded.format == 'JPEG'
    with Image.open(original) as decoded:
        assert decoded.format == 'AVIF'
