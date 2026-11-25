"""Send a validated frame to the TorchServe detector in the same replica."""

import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2

from ..errors import AppError


class TorchServeDetector:
    runtime_name = 'torchserve'

    def __init__(self, settings):
        self.url = f'http://127.0.0.1:{settings.torchserve_port}'
        deadline = time.monotonic() + 90
        while not self.is_ready():
            if time.monotonic() >= deadline:
                raise RuntimeError('TorchServe detector worker did not become ready.')
            time.sleep(1)

    def is_ready(self):
        try:
            with urlopen(f'{self.url}/ping', timeout=2) as response:
                return json.load(response).get('status') == 'Healthy'
        except (OSError, ValueError):
            return False

    def predict(self, image, threshold):
        encoded, frame = cv2.imencode('.png', image, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        if not encoded:
            raise AppError(500, 'encoding_error', 'Unable to prepare the detector input.')
        request = Request(
            f'{self.url}/predictions/eds-detector',
            data=frame.tobytes(),
            headers={'Content-Type': 'application/octet-stream', 'X-Detection-Threshold': str(threshold)},
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)['detections']
        except (URLError, TimeoutError, ValueError, KeyError) as exc:
            raise AppError(503, 'detector_unavailable', 'TorchServe could not detect the bus sign. Retry this frame.') from exc
