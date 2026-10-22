"""Independent OCR availability and shared crop preprocessing."""
import logging
import math

import cv2

from .easyocr import EasyOCRAdapter
from .tesseract import TesseractAdapter
from .trocr import TrOCRAdapter

ENGINE_IDS = ('easyocr', 'tesseract', 'trocr')


class OCRRegistry:
    def __init__(self, settings):
        self.adapters = {}
        self.errors = {}
        for name, factory in zip(ENGINE_IDS, (EasyOCRAdapter, TesseractAdapter, TrOCRAdapter)):
            try:
                self.adapters[name] = factory(settings)
            except Exception:
                logging.warning('OCR engine %s unavailable', name, exc_info=True)
                self.errors[name] = f'{name} is unavailable. Check its installed dependencies and local model files.'

    def backends(self):
        return list(self.adapters)

    def availability(self):
        return {name: self.errors.get(name) for name in ENGINE_IDS}

    def read(self, crop, field, backend):
        adapter = self.adapters[backend]
        height, width = crop.shape[:2]
        scale = min(4, max(1, 80 / height) if field == 'bus_number' else 1, 1000 / width)
        if scale != 1:
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        raw, confidence = adapter.read(crop, field)
        confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None and math.isfinite(confidence) else None
        return raw, confidence, adapter.confidence_method
