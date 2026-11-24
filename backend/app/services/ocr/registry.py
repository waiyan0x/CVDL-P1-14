"""Independent OCR availability and shared crop preprocessing."""
import logging
import math
from typing import get_args

import cv2

from ...schemas.analysis import Backend
from .easyocr import EasyOCRAdapter
from .paddleocr import PaddleOCRAdapter
from .trocr import TrOCRAdapter

ENGINE_IDS = get_args(Backend)
# Only this engine has a whole-display fallback: on whole EDS crops the pretrained
# PaddleOCR matched more displays than the fine-tuned one (11 vs 5 of 41,
# evaluation/ocr_scoring/whole-display-fallback-20261121/).
DISPLAY_FALLBACK_BACKEND = 'paddleocr'


def _clamp(confidence):
    return max(0.0, min(1.0, float(confidence))) if confidence is not None and math.isfinite(confidence) else None


class OCRRegistry:
    def __init__(self, settings):
        self.settings = settings
        self.display_reader = None
        self.display_error = None
        self.adapters = {}
        self.errors = {}
        # Looked up at call time so tests can substitute adapter classes.
        factories = {'easyocr': EasyOCRAdapter, 'paddleocr': PaddleOCRAdapter, 'trocr': TrOCRAdapter}
        for name in ENGINE_IDS:
            factory = factories[name]
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
        if scale != 1 and getattr(adapter, 'resize_input', True):
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        raw, confidence = adapter.read(crop, field)
        return raw, _clamp(confidence), adapter.confidence_method

    def read_display(self, crop):
        """Read a whole EDS crop with pretrained PaddleOCR; None if that model is unavailable.

        The worker starts on first use, so start-up is not slowed for frames that never need it.
        """
        if self.display_reader is None and self.display_error is None:
            try:
                self.display_reader = PaddleOCRAdapter(self.settings, fine_tuned=False)
            except Exception:
                logging.warning('Pretrained PaddleOCR whole-display fallback unavailable', exc_info=True)
                self.display_error = 'Pretrained PaddleOCR is unavailable.'
        if self.display_reader is None:
            return None
        raw, confidence = self.display_reader.read(crop, 'eds')
        return raw, _clamp(confidence), 'pretrained_whole_display_' + self.display_reader.confidence_method
