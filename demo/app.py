"""FastAPI app for uploaded images and browser-captured video/camera frames."""
from contextlib import asynccontextmanager
import io
import logging
from pathlib import Path

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .pipeline import Pipeline, ROOT

SAMPLE_DIR = ROOT / 'data/images/test'
PREFERRED = ['ea005707__9aebe21b-3.jpg', 'fce01393-3b0671f0-272.jpg',
             '49775ed2__a5dcfafd-122.jpg', '0c7ddfa8-27d65774-133.jpg']
SAMPLES = sorted([p for p in SAMPLE_DIR.glob('*.jpg') if not p.name.startswith('annotated_')],
                 key=lambda p: (PREFERRED.index(p.name) if p.name in PREFERRED else 99, p.name))
MAX_UPLOAD = 16 * 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    try:
        app.state.pipeline = await run_in_threadpool(Pipeline)
        app.state.error = None
    except Exception:
        logging.exception('Model initialization failed')
        app.state.pipeline = None
        app.state.error = 'Models could not load. Run setup and check the terminal log.'
    yield


app = FastAPI(title='Bus EDS Demo', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'demo/static'), name='static')


@app.get('/')
def index():
    return FileResponse(ROOT / 'demo/static/index.html')


@app.get('/api/health')
def health():
    pipeline = app.state.pipeline
    return {'ready': pipeline is not None, 'error': app.state.error,
            'detector': 'Supplied YOLO11n checkpoint', 'device': 'CPU',
            'backends': pipeline.ocr.backends() if pipeline else [],
            'default_backend': pipeline.ocr.backends()[0] if pipeline else None,
            'reference_rows': len(pipeline.matcher.rows) if pipeline else 0,
            'sample_count': len(SAMPLES),
            'confidence_note': 'OCR scores are backend-specific heuristics, not calibrated accuracy.'}


@app.get('/api/samples')
def samples():
    return [{'id': i, 'name': f'Project photo {i+1:02}', 'url': f'/api/samples/{i}/image',
             'source': p.name} for i, p in enumerate(SAMPLES)]


def sample_path(sample_id):
    if sample_id < 0 or sample_id >= len(SAMPLES):
        raise HTTPException(404, 'Sample not found.')
    return SAMPLES[sample_id]


@app.get('/api/samples/{sample_id}/image')
def sample_image(sample_id: int):
    return FileResponse(sample_path(sample_id))


def decode_image(data):
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, 'Image exceeds 16 MB. Choose a smaller image.')
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.width * original.height > 40_000_000:
                raise HTTPException(413, 'Image exceeds 40 megapixels.')
            image = ImageOps.exif_transpose(original).convert('RGB')
            image.thumbnail((1920, 1920))
            import numpy as np
            return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise HTTPException(400, 'Cannot decode this image. Use JPEG, PNG, or WebP.')


def run_recognition(data, detection, ocr_threshold, similarity, backend):
    pipeline = app.state.pipeline
    if pipeline is None:
        raise HTTPException(503, app.state.error)
    image = decode_image(data)
    if backend not in pipeline.ocr.backends():
        raise HTTPException(400, 'Selected OCR backend is unavailable.')
    if not pipeline.lock.acquire(blocking=False):
        raise HTTPException(429, 'Another frame is being processed. Try again shortly.')
    try:
        return pipeline.recognise(image, detection, ocr_threshold, similarity, backend)
    except Exception as exc:
        logging.exception('Recognition failed')
        raise HTTPException(500, 'Recognition failed. Check the terminal log or choose another OCR engine.') from exc
    finally:
        pipeline.lock.release()


@app.post('/api/recognize')
def recognise(file: UploadFile = File(...), detection: float = Form(.3, ge=.05, le=.95),
              ocr_threshold: float = Form(.25, ge=0, le=1), similarity: float = Form(.7, ge=0, le=1),
              backend: str = Form('easyocr')):
    return run_recognition(file.file.read(MAX_UPLOAD + 1), detection, ocr_threshold, similarity, backend)


@app.post('/api/samples/{sample_id}/recognize')
def recognise_sample(sample_id: int, detection: float = Form(.3, ge=.05, le=.95),
                     ocr_threshold: float = Form(.25, ge=0, le=1), similarity: float = Form(.7, ge=0, le=1),
                     backend: str = Form('easyocr')):
    return run_recognition(sample_path(sample_id).read_bytes(), detection, ocr_threshold, similarity, backend)
