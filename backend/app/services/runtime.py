"""One process owns one detector and admits inference without a pending queue."""
import logging
import threading
from contextlib import contextmanager

from ..errors import AppError
from .detection import Detector
from .matching import RouteMatcher
from .ocr.registry import OCRRegistry
from .pipeline import Pipeline


class Runtime:
    def __init__(self, settings):
        self.settings = settings
        self.pipeline = None
        self.error = None
        self.lock = threading.Lock()

    def start(self):
        try:
            detector = Detector(self.settings)
            ocr = OCRRegistry(self.settings)
            matcher = RouteMatcher(self.settings.root / 'data/bus_information.csv')
            self.pipeline = Pipeline(self.settings, detector, ocr, matcher)
            if not self.backends:
                self.error = 'No OCR engines are available. Run setup and check local model files.'
        except Exception:
            logging.exception('Application model initialization failed')
            self.error = 'Models could not load. Run setup and check the server log.'
        return self

    @property
    def backends(self):
        return self.pipeline.ocr.backends() if self.pipeline else []

    @property
    def ready(self):
        return self.pipeline is not None and bool(self.backends)

    @contextmanager
    def admit(self, backend=None):
        if not self.ready:
            raise AppError(503, 'models_not_ready', self.error or 'Models are still loading.')
        if backend is not None and backend not in self.backends:
            raise AppError(400, 'engine_unavailable', 'Selected OCR engine is unavailable. Choose another engine.')
        if not self.lock.acquire(blocking=False):
            raise AppError(429, 'processing_busy', 'Another frame is processing. Skip this frame and retry later.')
        try:
            yield self.pipeline
        finally:
            self.lock.release()
