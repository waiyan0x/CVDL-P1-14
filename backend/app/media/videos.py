"""Bounded local video uploads with explicit seeking and temporary-file ownership."""
import math
import threading
import time
from pathlib import Path
from uuid import uuid4

import cv2

from ..errors import AppError


class VideoStore:
    def __init__(self, settings):
        self.settings = settings
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.entries = {}
        self.lock = threading.RLock()
        # Clean abandoned uploads only after their configured lifetime.
        for path in settings.upload_dir.glob('*.upload'):
            if time.time() - path.stat().st_mtime > settings.video_ttl_seconds:
                path.unlink(missing_ok=True)

    def _expire(self):
        for identity, entry in list(self.entries.items()):
            if time.monotonic() - entry['touched'] > self.settings.video_ttl_seconds:
                self.delete(identity)

    def add(self, stream, name):
        with self.lock:
            self._expire()
            if len(self.entries) >= self.settings.max_video_uploads:
                raise AppError(429, 'upload_limit', 'Too many open videos. Reset an existing video first.')
            identity = uuid4().hex
            path = self.settings.upload_dir / f'{identity}.upload'
            try:
                total = 0
                with path.open('wb') as output:
                    while chunk := stream.read(1024 * 1024):
                        total += len(chunk)
                        if total > self.settings.max_video_bytes:
                            raise AppError(413, 'video_too_large', 'Video exceeds the configured upload limit.')
                        output.write(chunk)
                metadata = self._probe(path)
                entry = {**metadata, 'video_id': identity, 'name': Path((name or 'video').replace('\\', '/')).name[:180],
                         'url': f'/api/videos/{identity}/content', 'path': path, 'touched': time.monotonic()}
                self.entries[identity] = entry
                return self._public(entry)
            except BaseException:
                path.unlink(missing_ok=True)
                raise

    @staticmethod
    def _public(entry):
        return {key: value for key, value in entry.items() if key not in ('path', 'touched')}

    def _probe(self, path):
        with path.open('rb') as source:
            magic = source.read(16)
        supported = magic[4:8] == b'ftyp' or (magic[:4] == b'RIFF' and magic[8:12] == b'AVI ') or magic[:4] == b'\x1aE\xdf\xa3'
        if not supported:
            raise AppError(400, 'unsupported_video', 'Unsupported video container. Use MP4, MOV, WebM or AVI.')
        capture = cv2.VideoCapture(str(path))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if not all(math.isfinite(value) and value > 0 for value in (fps, count, width, height)):
                raise AppError(400, 'unsupported_video', 'Cannot read this video. Its codec may be unsupported.')
            if width * height > self.settings.max_image_pixels:
                raise AppError(413, 'video_too_large', 'Video resolution exceeds the configured pixel limit.')
            duration = count / fps
            if duration > self.settings.max_video_duration_seconds:
                raise AppError(413, 'video_too_long', 'Video duration exceeds the configured limit.')
            ok, first = capture.read()
            if not ok or first is None:
                raise AppError(400, 'invalid_video', 'This video contains no decodable frames.')
            return {'width': first.shape[1], 'height': first.shape[0], 'duration_ms': round(duration * 1000, 3),
                    'fps': round(fps, 6)}
        finally:
            capture.release()

    def get(self, identity):
        with self.lock:
            self._expire()
            entry = self.entries.get(identity)
            if entry is None:
                raise AppError(404, 'video_not_found', 'Video expired or was removed. Upload it again.')
            entry['touched'] = time.monotonic()
            return entry

    def frame(self, identity, timestamp_ms):
        with self.lock:
            entry = self.get(identity)
            if not math.isfinite(timestamp_ms) or timestamp_ms < 0 or timestamp_ms >= entry['duration_ms']:
                raise AppError(400, 'timestamp_out_of_range', 'Choose a position within the uploaded video.')
            capture = cv2.VideoCapture(str(entry['path']))
            try:
                index = int(timestamp_ms * entry['fps'] / 1000)
                positioned = capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                if index and not positioned:
                    raise AppError(400, 'video_seek_error', 'This video cannot be sampled at the requested position. Try another file.')
                ok, image = capture.read()
                if not ok or image is None:
                    raise AppError(400, 'video_decode_error', 'Cannot decode this position in the video. Try another file.')
                actual_index = max(0, capture.get(cv2.CAP_PROP_POS_FRAMES) - 1)
                actual_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
                if not math.isfinite(actual_ms) or (actual_ms <= 0 and actual_index > 0):
                    actual_ms = actual_index * 1000 / entry['fps']
                return image, round(actual_ms, 3)
            finally:
                capture.release()

    def delete(self, identity):
        with self.lock:
            entry = self.entries.pop(identity, None)
            if entry:
                entry['path'].unlink(missing_ok=True)

    def close(self):
        with self.lock:
            for identity in list(self.entries):
                self.delete(identity)
