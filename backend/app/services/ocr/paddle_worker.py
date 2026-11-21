"""PaddleOCR recognition worker, run in the separate Paddle Python environment.

The app's own Python cannot import PaddlePaddle, so the adapter starts this file
with the Paddle interpreter and exchanges one JSON object per line:

    request:  {"png_b64": "<PNG bytes, base64>"}
    response: {"text": str, "confidence": float | null, "line_count": int,
               "segmentation": str, "error": str | null}

Reading follows the saved benchmark for new crops: automatic row-projection
line segmentation on the RGB crop, grayscale line images, top-to-bottom order,
newline-joined lines and a character-weighted mean of Paddle line scores. If
segmentation is unresolved, no whole-crop reading is substituted.
"""
import base64
import io
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]


def _protocol_stream():
    # Paddle writes logs to stdout; keep the real stdout for protocol messages only.
    stream = os.fdopen(os.dup(1), 'w', buffering=1, encoding='utf-8')
    os.dup2(2, 1)
    return stream


def _recognise(png_bytes, segment_lines, reader):
    import numpy as np
    from PIL import Image
    with Image.open(io.BytesIO(png_bytes)) as image:
        rgb = np.asarray(image.convert('RGB'))
    gray, regions, info = segment_lines(rgb)
    if not regions:
        return {'text': '', 'confidence': None, 'line_count': 0, 'segmentation': info['status'],
                'error': f"Line segmentation unresolved: {info['status']}"}
    lines = []
    for _, top, width, bottom in regions:
        [(_, text, score)] = reader.recognize(gray[top:bottom, 0:width])
        lines.append((text, score if math.isfinite(score) else None))
    scored = [(text, score) for text, score in lines if text]
    chars = sum(len(text) for text, _ in scored)
    confidence = (sum(len(text) * score for text, score in scored) / chars
                  if chars and all(score is not None for _, score in scored) else None)
    return {'text': '\n'.join(text for text, _ in lines), 'confidence': confidence,
            'line_count': len(lines), 'segmentation': info['status'], 'error': None}


def main():
    model_dir = Path(sys.argv[1]).resolve()
    out = _protocol_stream()
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
    os.environ.setdefault('DISABLE_MODEL_SOURCE_CHECK', 'True')
    os.environ.setdefault('PADDLE_PDX_CACHE_HOME', str(ROOT / '.cache/paddle-runtime'))
    sys.path.insert(0, str(ROOT))
    try:
        from paddleocr import TextRecognition
        from backend.app.evaluation.ocr_crop_baseline import segment_lines
        from backend.app.evaluation.paddle_crop_reader import PaddleCropReader
        reader = PaddleCropReader(TextRecognition(model_name='en_PP-OCRv5_mobile_rec', model_dir=str(model_dir),
                                                  device='cpu', enable_mkldnn=False, cpu_threads=2))
    except Exception as exc:
        out.write(json.dumps({'ready': False, 'error': f'{type(exc).__name__}: {exc}'}) + '\n')
        return 1
    out.write(json.dumps({'ready': True}) + '\n')
    for request in sys.stdin:
        try:
            png = base64.b64decode(json.loads(request)['png_b64'], validate=True)
            response = _recognise(png, segment_lines, reader)
        except Exception as exc:
            response = {'text': '', 'confidence': None, 'line_count': 0, 'segmentation': None,
                        'error': f'{type(exc).__name__}: {exc}'}
        out.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
