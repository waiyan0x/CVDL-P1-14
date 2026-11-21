"""Selected fine-tuned PaddleOCR, run in a persistent worker process.

PaddlePaddle is installed in its own Python environment (the app's Python is
newer than Paddle supports), so recognition happens in `paddle_worker.py`,
started once with that interpreter and reused for every crop.
"""
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import selectors
import subprocess
import threading

import cv2

WORKER = Path(__file__).with_name('paddle_worker.py')
READY_TIMEOUT_SECONDS = 180
READ_TIMEOUT_SECONDS = 30


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_model(model_dir, fine_tuned=True):
    """Refuse weights whose hashes differ from their provenance record."""
    kind = 'fine-tuned' if fine_tuned else 'pretrained'
    provenance_path = model_dir / 'provenance.json'
    if not provenance_path.is_file():
        raise RuntimeError(f'{kind.capitalize()} PaddleOCR weights are missing; copy them into the model folder.')
    provenance = json.loads(provenance_path.read_text())
    if (provenance.get('repository') != 'PaddlePaddle/en_PP-OCRv5_mobile_rec'
            or bool(provenance.get('fine_tuned')) != fine_tuned):
        raise RuntimeError(f'PaddleOCR provenance does not describe the {kind} model.')
    for name, expected in provenance['files_sha256'].items():
        file = model_dir / name
        if not file.is_file() or _sha256(file) != expected:
            raise RuntimeError(f'PaddleOCR model file {name} is missing or differs from its recorded hash.')
    return provenance


class PaddleOCRAdapter:
    confidence_method = 'character_weighted_line_score'
    # Feed crops at native size, as in the saved benchmark; the worker segments lines itself.
    resize_input = False

    def __init__(self, settings, fine_tuned=True):
        self.python = settings.paddle_python_path
        self.model_dir = settings.paddle_model_dir if fine_tuned else settings.paddle_pretrained_dir
        if not self.python.is_file():
            raise RuntimeError('The PaddleOCR Python environment is missing; set EDS_PADDLE_PYTHON or create it.')
        verify_model(self.model_dir, fine_tuned)
        self.log_path = settings.root / '.runtime/logs/paddle_worker.log'
        self.lock = threading.Lock()
        self.process = None
        self._start()

    def _start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'PYTHONUNBUFFERED': '1'}
        with self.log_path.open('a') as log:
            # -I keeps this folder off sys.path, so this module cannot shadow the real `paddleocr` package.
            self.process = subprocess.Popen(
                [str(self.python), '-I', str(WORKER), str(self.model_dir)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, encoding='utf-8', env=env)
        try:
            ready = self._receive(READY_TIMEOUT_SECONDS).get('ready')
        except Exception:
            ready = False
        if not ready:
            self.close()
            raise RuntimeError(f'PaddleOCR worker failed to load the model; see {self.log_path}.')

    def _receive(self, timeout):
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            if not selector.select(timeout):
                raise TimeoutError('PaddleOCR worker did not respond in time.')
        finally:
            selector.close()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('PaddleOCR worker stopped unexpectedly.')
        return json.loads(line)

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)

    def read(self, crop, field):
        ok, encoded = cv2.imencode('.png', crop)
        if not ok:
            return '', 0.0
        request = json.dumps({'png_b64': base64.b64encode(encoded.tobytes()).decode('ascii')}) + '\n'
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._start()
            try:
                self.process.stdin.write(request)
                self.process.stdin.flush()
                response = self._receive(READ_TIMEOUT_SECONDS)
            except Exception:
                # Leave no half-answered request in the pipe; restart on the next crop.
                self.close()
                raise
        if response.get('error'):
            logging.info('PaddleOCR returned no reading: %s', response['error'])
        confidence = response.get('confidence')
        return response.get('text', ''), confidence if confidence is not None else 0.0
