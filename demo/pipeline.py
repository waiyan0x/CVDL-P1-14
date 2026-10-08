"""YOLO field detection, OCR, and reference matching without a bus-detection gate."""
import base64
import re
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from .matching import RouteMatcher
from .ocr import OCR

ROOT = Path(__file__).resolve().parents[1]


def jpeg_data(image):
    ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError('Unable to encode image.')
    return 'data:image/jpeg;base64,' + base64.b64encode(data).decode()


def pair_fields(fields):
    """Pair nearby, vertically overlapping fields; preserve separate bus results."""
    numbers = sorted([f for f in fields if f['label'] == 'bus_number'], key=lambda f: -f['confidence'])[:3]
    destinations = [f for f in fields if f['label'] == 'destination']
    groups = []
    used = set()
    for number in numbers:
        x1, y1, x2, y2 = number['box']
        height = max(y2 - y1, 1)
        possible = []
        for index, dest in enumerate(destinations):
            a, b, c, d = dest['box']
            overlap = max(0, min(y2, d) - max(y1, b)) / max(1, min(height, d-b))
            distance = min(abs(x1-c), abs(a-x2))
            if index not in used and overlap >= .25 and distance < 12 * height:
                possible.append((distance + abs((y1+y2-b-d)/2) * 3, index, dest))
        if possible:
            _, index, dest = min(possible, key=lambda item: item[0])
            used.add(index)
        else:
            dest = None
        groups.append((number, dest))
    groups.extend((None, dest) for i, dest in enumerate(destinations) if i not in used)
    return groups[:3]


class Pipeline:
    def __init__(self):
        torch.set_num_threads(4)
        self.model = YOLO(str(ROOT / 'models/yolo-v6-finetuned/best_v6.pt'))
        self.ocr = OCR(ROOT)
        self.matcher = RouteMatcher(ROOT / 'data/bus_information.csv')
        self.lock = threading.Lock()
        self.model.predict(np.zeros((640, 640, 3), dtype=np.uint8), device='cpu', verbose=False)

    def recognise(self, image, detection=.3, ocr_threshold=.25, similarity=.7, backend='easyocr'):
        if backend not in self.ocr.backends():
            raise ValueError('Selected OCR backend is unavailable.')
        start = time.perf_counter()
        # Bound image size and model cost; returned boxes use the returned preview coordinates.
        height, width = image.shape[:2]
        scale = min(1, 1920 / max(height, width))
        if scale < 1:
            image = cv2.resize(image, (round(width*scale), round(height*scale)))
        prediction = self.model.predict(image, device='cpu', imgsz=640, conf=detection,
                                        classes=[1, 2, 3], max_det=12, verbose=False)[0]
        detection_ms = (time.perf_counter() - start) * 1000
        height, width = image.shape[:2]
        fields = []
        for box in prediction.boxes:
            cls = int(box.cls.item())
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            coordinates = [max(0, min(x1, width-1)), max(0, min(y1, height-1)),
                           max(1, min(x2, width)), max(1, min(y2, height))]
            if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
                continue
            fields.append({'label': self.model.names[cls], 'box': coordinates,
                           'confidence': round(float(box.conf.item()), 3)})
        results = []
        for number, destination in pair_fields(fields):
            recognised = {}
            for field in [number, destination]:
                if field is None:
                    continue
                x1, y1, x2, y2 = field['box']
                crop = image[y1:y2,x1:x2]
                raw, confidence = self.ocr.read(crop, field['label'], backend)
                recognised[field['label']] = {**field, 'raw': raw,
                    'ocr_confidence': round(confidence, 3), 'crop': jpeg_data(crop)}
            num = recognised.get('bus_number', {})
            dest = recognised.get('destination', {})
            service_raw = num.get('raw', '')
            # Only isolated service-like strings qualify, preserving raw text for inspection.
            service = re.sub(r'\s+', '', service_raw.upper())
            valid_number = re.fullmatch(r'[0-9]{1,3}[A-Z]{0,2}', service)
            usable = bool(valid_number) and num.get('ocr_confidence', 0) >= ocr_threshold
            destination_raw = dest.get('raw', '') if dest.get('ocr_confidence', 0) >= ocr_threshold else ''
            match = self.matcher.match(service if usable else '', destination_raw, similarity)
            results.append({'fields': recognised, 'match': match,
                            'message': 'Bus information recognised' if usable else 'No bus information detected'})
        latency = (time.perf_counter() - start) * 1000
        return {'image': jpeg_data(image), 'width': width, 'height': height, 'detections': fields,
                'results': results, 'backend': backend, 'latency_ms': round(latency),
                'detection_ms': round(detection_ms), 'processing_fps': round(1000 / latency, 2),
                'message': 'Display regions detected' if results else 'No bus information detected'}
