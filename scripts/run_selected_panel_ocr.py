"""Recognize inventoried whole EDS panels, or one new crop, with local Paddle weights."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-dir', type=Path, required=True)
    ap.add_argument('--inventory', type=Path)
    ap.add_argument('--crop', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if bool(a.inventory) == bool(a.crop):
        ap.error('Choose --inventory or --crop')
    if a.output.exists():
        raise FileExistsError(a.output)
    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    os.environ['PADDLE_PDX_CACHE_HOME'] = str(ROOT / '.cache/paddle-runtime')
    from paddleocr import TextRecognition
    from PIL import Image
    from backend.app.evaluation.ocr_crop_baseline import recognize_crop, sha256
    from backend.app.evaluation.paddle_crop_reader import PaddleCropReader
    provenance = json.loads((a.model_dir / 'provenance.json').read_text())
    assert provenance['fine_tuned'] is True
    for name, expected in provenance['files_sha256'].items():
        if sha256(a.model_dir / name) != expected:
            raise ValueError('Model hash mismatch: ' + name)
    records = json.loads(a.inventory.read_text()) if a.inventory else []
    if a.crop:
        with Image.open(a.crop) as im:
            width, height = im.size
        records = [dict(review_id='NEW_CROP', crop_path=str(a.crop.resolve()),
                        crop_id=a.crop.name, crop_set='new', field='front_eds',
                        crop_sha256=sha256(a.crop), input_width=width, input_height=height)]
    model = TextRecognition(model_name='en_PP-OCRv5_mobile_rec', model_dir=str(a.model_dir),
                            device='cpu', enable_mkldnn=False, cpu_threads=2)
    reader = PaddleCropReader(model)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        for index, record in enumerate(records, 1):
            result = recognize_crop(record, reader, lambda: None)
            f.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + '\n')
            f.flush()
            if index % 25 == 0 or index == len(records):
                print(f'{index}/{len(records)} panels', flush=True)
    print('Saved', a.output)


if __name__ == '__main__':
    main()
