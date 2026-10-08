import io
import threading
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image
import pytest

import demo.app as module


class FakePipeline:
    def __init__(self):
        self.lock = threading.Lock()
        self.ocr = SimpleNamespace(backends=lambda: ['easyocr'])
        self.matcher = SimpleNamespace(rows=[{}])

    def recognise(self, image, *args):
        return {'width': image.shape[1], 'height': image.shape[0], 'results': []}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(module, 'Pipeline', FakePipeline)
    with TestClient(module.app) as client:
        yield client


def test_bad_image_is_rejected(client):
    response = client.post('/api/recognize', files={'file': ('bad.jpg', b'not an image')})
    assert response.status_code == 400


def test_oversized_upload_is_rejected(client):
    response = client.post('/api/recognize', files={'file': ('big.jpg', b'a' * (module.MAX_UPLOAD+1))})
    assert response.status_code == 413


def test_invalid_sample_and_threshold_are_rejected(client):
    assert client.get('/api/samples/-1/image').status_code == 404
    assert client.post('/api/samples/9999/recognize').status_code == 404
    assert client.post('/api/samples/0/recognize', data={'detection': 10}).status_code == 422


def test_missing_engine_and_busy_server_have_clear_errors(client):
    assert client.post('/api/samples/0/recognize', data={'backend': 'missing'}).status_code == 400
    lock = module.app.state.pipeline.lock
    lock.acquire()
    try:
        assert client.post('/api/samples/0/recognize').status_code == 429
    finally:
        lock.release()


def test_input_coordinates_match_resized_preview(client):
    stream = io.BytesIO()
    Image.new('RGB', (3000, 1500)).save(stream, format='JPEG')
    response = client.post('/api/recognize', files={'file': ('wide.jpg', stream.getvalue())})
    assert response.status_code == 200
    assert response.json() == {'width': 1920, 'height': 960, 'results': []}


def test_sample_list_does_not_include_annotated_test_image(client):
    samples = client.get('/api/samples').json()
    assert len(samples) == 14
    assert not any('annotated_' in s['source'] for s in samples)
