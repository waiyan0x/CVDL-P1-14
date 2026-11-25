"""Serve the project's detector from its reviewed checkpoint in TorchServe."""

from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from ts.utils.util import PredictionException

from detection import Detector


class EDSHandler:
    def initialize(self, context):
        model_dir = Path(context.system_properties['model_dir'])
        checkpoint = model_dir / context.manifest['model']['serializedFile']
        self.detector = Detector(SimpleNamespace(
            detector_path=checkpoint,
            detector_weights=checkpoint,
            detector_device='cpu',
            detector_image_size=640,
            detector_nms_iou=0.70,
            torch_threads=2,
        ))

    def handle(self, requests, context):
        predictions = []
        for index, request in enumerate(requests):
            body = request.get('body') or request.get('data')
            if not isinstance(body, (bytes, bytearray)):
                raise PredictionException('Send an image as the raw request body.', 400)
            headers = {key.lower(): value for key, value in context.get_all_request_header(index).items()}
            try:
                threshold = float(headers.get('x-detection-threshold', '0.50'))
                if not 0.05 <= threshold <= 0.95:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise PredictionException('Detection threshold must be between 0.05 and 0.95.', 400) from exc
            image = cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None or max(image.shape[:2]) > 1920:
                raise PredictionException('Send a decodable frame no larger than 1920 pixels per side.', 400)
            predictions.append({'detections': self.detector.predict(image, threshold)})
        return predictions
