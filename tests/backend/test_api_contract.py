import io
import threading

from fastapi.testclient import TestClient
import numpy as np
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
        reference = self.settings.root / 'routes.csv'
        reference.write_text('Route number,Origin,Destination\n3,A,B\n')
        self.pipeline = Pipeline(self.settings, EmptyDetector(), Engines(), RouteMatcher(reference))
        return self


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(root=tmp_path, max_image_bytes=2048), FakeRuntime)
    with TestClient(app) as client:
        yield client


def jpeg():
    stream = io.BytesIO()
    Image.new('RGB', (80, 60)).save(stream, 'JPEG')
    return stream.getvalue()


def test_analysis_metadata_and_no_eds_status(client):
    response = client.post('/api/analysis', files={'file': ('frame.jpg', jpeg(), 'image/jpeg')},
        data={'session_id': 'camera-session', 'frame_id': 9, 'source': 'camera',
              'source_timestamp_ms': 350, 'captured_at': '2026-10-22T10:00:00+08:00'})
    assert response.status_code == 200
    data = response.json()
    assert data['frame']['session_id'] == 'camera-session'
    assert data['frame']['frame_id'] == 9
    assert data['frame']['source_timestamp_ms'] == 350
    assert data['status'] == 'no_eds'
    assert data['results'] == []


def test_invalid_inputs_use_one_error_shape(client):
    responses = [
        client.post('/api/analysis'),
        client.post('/api/analysis', files={'file': ('bad.jpg', b'invalid')}),
        client.post('/api/analysis', files={'file': ('big.jpg', b'a' * 2049)}),
        client.post('/api/analysis', files={'file': ('frame.jpg', jpeg())}, data={'detection': 10}),
        client.post('/api/analysis', files={'file': ('frame.jpg', jpeg())}, data={'frame_id': -1}),
    ]
    assert [r.status_code for r in responses] == [400, 400, 413, 422, 422]
    assert all(set(r.json()['error']) == {'code', 'message'} for r in responses)


def test_busy_request_rejected_before_invalid_image_decode(client):
    lock = client.app.state.runtime.lock
    lock.acquire()
    try:
        response = client.post('/api/analysis', files={'file': ('bad.jpg', b'invalid')})
        assert response.status_code == 429
        assert response.json()['error']['code'] == 'processing_busy'
    finally:
        lock.release()


def test_unavailable_engine_and_missing_video_are_clear(client):
    response = client.post('/api/analysis', files={'file': ('frame.jpg', jpeg())}, data={'backend': 'trocr'})
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'engine_unavailable'
    response = client.post('/api/videos/missing/frames', json={'timestamp_ms': 0})
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'video_not_found'
    assert client.delete('/api/videos/missing').status_code == 204


def test_comparison_keeps_unavailable_engine_entries(client):
    response = client.post('/api/comparisons', files={'file': ('frame.jpg', jpeg())})
    assert response.status_code == 200
    entries = response.json()['comparisons']
    assert [entry['status'] for entry in entries] == ['success', 'unavailable', 'unavailable']


def test_health_does_not_claim_missing_engines(client):
    data = client.get('/api/health').json()
    assert data['ready'] is True
    assert data['backends'] == ['easyocr']
    assert data['limits']['image_upload_bytes'] == 2048


def test_request_body_limit_rejects_before_multipart_decode(client):
    response = client.post('/api/analysis', content=b'x', headers={'content-length': str(3 * 1024 * 1024), 'content-type': 'multipart/form-data; boundary=x'})
    assert response.status_code == 413
    assert response.json()['error']['code'] == 'request_too_large'


def test_streaming_body_limit_is_enforced_without_content_length(client):
    boundary = 'frame-boundary'
    chunks = [f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="large.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode(),
              b'a' * (2 * 1024 * 1024), f'\r\n--{boundary}--\r\n'.encode()]
    response = client.post('/api/analysis', content=iter(chunks), headers={'content-type': f'multipart/form-data; boundary={boundary}'})
    assert response.status_code == 413
    assert response.json()['error']['code'] == 'request_too_large'


def test_video_upload_frame_identity_and_api_cleanup(client, tmp_path):
    import cv2
    path = tmp_path / 'clip.avi'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 10, (80, 60))
    assert writer.isOpened()
    for _ in range(5):
        writer.write(np.zeros((60, 80, 3), np.uint8))
    writer.release()
    response = client.post('/api/videos', files={'file': ('clip.avi', path.read_bytes(), 'video/x-msvideo')})
    assert response.status_code == 200
    media = response.json()
    response = client.post(f"/api/videos/{media['video_id']}/frames", json={'timestamp_ms': 250,
        'session_id': 'uploaded-video', 'frame_id': 8, 'source': 'video', 'source_timestamp_ms': 250})
    assert response.status_code == 200
    data = response.json()
    assert data['frame']['source_timestamp_ms'] == pytest.approx(200, abs=1)
    assert data['frame']['frame_id'] == 8
    assert data['frame']['session_id'] == 'uploaded-video'
    assert client.delete(f"/api/videos/{media['video_id']}").status_code == 204
    assert client.get(media['url']).status_code == 404
