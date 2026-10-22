"""Original demo regression scenarios migrated to the application API."""
import io

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.pipeline import Pipeline
from backend.app.services.matching import RouteMatcher
from backend.app.services.runtime import Runtime


class EmptyDetector:
    def predict(self, image, threshold):
        return []


class Engines:
    def backends(self):
        return ['easyocr']


class FakeRuntime(Runtime):
    def start(self):
        self.pipeline = Pipeline(self.settings, EmptyDetector(), Engines(),
                                 RouteMatcher(self.settings.root / 'data/bus_information.csv'))
        return self


@pytest.fixture
def client():
    with TestClient(create_app(Settings(), FakeRuntime)) as client:
        yield client


def test_bad_image_is_rejected(client):
    response = client.post('/api/analysis', files={'file': ('bad.jpg', b'not an image')})
    assert response.status_code == 400


def test_oversized_upload_is_rejected(client):
    response = client.post('/api/analysis', files={'file': ('big.jpg', b'a' * (16 * 1024 * 1024 + 1))})
    assert response.status_code == 413


def test_invalid_sample_and_threshold_are_rejected(client):
    assert client.get('/api/samples/-1/image').status_code == 404
    assert client.post('/api/analysis', data={'sample_id': 9999}).status_code == 404
    assert client.post('/api/analysis', data={'sample_id': 0, 'detection': 10}).status_code == 422


def test_missing_engine_and_busy_server_have_clear_errors(client):
    assert client.post('/api/analysis', data={'sample_id': 0, 'backend': 'trocr'}).status_code == 400
    lock = client.app.state.runtime.lock
    lock.acquire()
    try:
        assert client.post('/api/analysis', data={'sample_id': 0}).status_code == 429
    finally:
        lock.release()


def test_input_coordinates_match_resized_preview(client):
    stream = io.BytesIO()
    Image.new('RGB', (3000, 1500)).save(stream, format='JPEG')
    response = client.post('/api/analysis', files={'file': ('wide.jpg', stream.getvalue())})
    assert response.status_code == 200
    data = response.json()
    assert (data['width'], data['height'], data['results']) == (1920, 960, [])


def test_sample_list_does_not_include_annotated_test_image(client):
    samples = client.get('/api/samples').json()
    assert len(samples) == 18  # Four design-reference photos and 14 original project photos.
    assert not any('annotated_' in sample['source'] for sample in samples)
