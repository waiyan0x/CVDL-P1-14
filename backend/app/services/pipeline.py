"""Shared detector/crops followed by independently selectable OCR and matching."""
import logging
import time
from datetime import datetime, timezone

from ..media.images import jpeg_data, resize_frame
from .association import associate_displays
from .ocr.registry import ENGINE_IDS
from .results import MESSAGES, frame_status, match_fields


class Pipeline:
    def __init__(self, settings, detector, ocr, matcher):
        self.settings, self.detector, self.ocr, self.matcher = settings, detector, ocr, matcher

    def prepare(self, image, options, started=None):
        started = started if started is not None else time.perf_counter()
        image = resize_frame(image, self.settings.preview_max_side)
        preprocessing_ms = (time.perf_counter() - started) * 1000
        detection_start = time.perf_counter()
        predictions = self.detector.predict(image, options.detection)
        detection_ms = (time.perf_counter() - detection_start) * 1000
        post_start = time.perf_counter()
        height, width = image.shape[:2]
        groups, detections = associate_displays(predictions, width, height)
        crops = {}
        for group in groups:
            for field in list(group['fields'].values()) + ([group['screen']] if group['screen'] else []):
                x1, y1, x2, y2 = field['box']
                crop = image[y1:y2, x1:x2].copy()
                crops[field['id']] = (crop, jpeg_data(crop))
        preview = jpeg_data(image)
        preprocessing_ms += (time.perf_counter() - post_start) * 1000
        return {'image': preview, 'width': width, 'height': height, 'detections': detections,
                'groups': groups, 'crops': crops, 'preprocessing_ms': preprocessing_ms, 'detection_ms': detection_ms}

    def recognise(self, prepared, options, backend):
        results, ocr_ms, matching_ms = [], 0.0, 0.0
        for group in prepared['groups']:
            fields = {}
            for label, field in group['fields'].items():
                crop, encoded = prepared['crops'][field['id']]
                started = time.perf_counter()
                raw, confidence, method = self.ocr.read(crop, label, backend)
                ocr_ms += (time.perf_counter() - started) * 1000
                fields[label] = {**field, 'raw': raw, 'ocr_confidence': round(confidence, 4) if confidence is not None else None,
                                 'ocr_confidence_method': method, 'crop': encoded}
            started = time.perf_counter()
            status, match = match_fields(fields, self.matcher, options)
            matching_ms += (time.perf_counter() - started) * 1000
            screen = group['screen']
            results.append({'display_id': group['display_id'], 'status': status, 'message': MESSAGES[status],
                'screen': {**screen, 'crop': prepared['crops'][screen['id']][1]} if screen else None,
                'fields': fields, 'match': match})
        timings = {key: prepared[key] for key in ('preprocessing_ms', 'detection_ms')}
        timings.update(ocr_ms=ocr_ms, matching_ms=matching_ms)
        total_ms = sum(timings.values())
        timings['total_ms'] = total_ms
        status = frame_status(results)
        frame = {**options.frame(), 'processed_at': datetime.now(timezone.utc).isoformat()}
        return {'frame': frame, 'status': status, 'message': MESSAGES[status], 'backend': backend,
                **{key: prepared[key] for key in ('image', 'width', 'height', 'detections')},
                'results': results, 'timings': {key: round(value, 3) for key, value in timings.items()},
                'processing_fps': round(1000 / max(total_ms, .001), 2)}

    def analyse(self, image, options, started=None):
        return self.recognise(self.prepare(image, options, started), options, options.backend)

    def compare(self, image, options, started=None):
        prepared = self.prepare(image, options, started)
        comparisons = []
        for backend in ENGINE_IDS:
            if backend not in self.ocr.backends():
                comparisons.append({'backend': backend, 'status': 'unavailable', 'result': None,
                                    'error': f'{backend} is unavailable. Check its dependencies and local model files.'})
                continue
            try:
                result = self.recognise(prepared, options, backend)
                comparisons.append({'backend': backend, 'status': 'success', 'result': result, 'error': None})
            except Exception:
                logging.exception('Comparison engine %s failed', backend)
                comparisons.append({'backend': backend, 'status': 'error', 'result': None,
                                    'error': f'{backend} failed to process this image. Try another engine or check the server log.'})
        return {'frame': {**options.frame(), 'processed_at': datetime.now(timezone.utc).isoformat()},
                **{key: prepared[key] for key in ('image', 'width', 'height', 'detections')}, 'comparisons': comparisons}
