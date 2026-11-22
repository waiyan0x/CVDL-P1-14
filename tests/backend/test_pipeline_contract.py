import numpy as np

from backend.app.config import Settings
from backend.app.schemas.analysis import FrameOptions, AnalysisResponse
from backend.app.services.pipeline import Pipeline
from backend.app.services.matching import RouteMatcher


class Detector:
    def __init__(self, fields):
        self.fields = fields
        self.calls = 0

    def predict(self, image, threshold):
        self.calls += 1
        return self.fields


class Engines:
    def backends(self):
        return ['easyocr', 'paddleocr']

    def read(self, crop, field, backend):
        if backend == 'paddleocr':
            raise RuntimeError('a private adapter detail')
        return ('3' if field == 'bus_number' else 'Tampines Int'), .9, 'test_score'


def pipeline(tmp_path, fields):
    reference = tmp_path / 'routes.csv'
    reference.write_text('Route number,Origin,Destination\n3,Punggol Int,Tampines Int\n')
    return Pipeline(Settings(root=tmp_path), Detector(fields), Engines(), RouteMatcher(reference))


def test_screen_only_result_is_unreadable_with_screen_crop(tmp_path):
    service = pipeline(tmp_path, [{'label': 'eds', 'box': [0, 0, 100, 40], 'confidence': .8}])
    result = service.analyse(np.zeros((60, 120, 3), np.uint8), FrameOptions(session_id='camera', frame_id=12))
    parsed = AnalysisResponse.model_validate(result)
    assert parsed.status == 'unreadable'
    assert parsed.results[0].screen.crop.startswith('data:image/jpeg;base64,')
    assert parsed.frame.frame_id == 12
    assert parsed.frame.session_id == 'camera'


def test_comparison_detects_once_and_isolates_engine_failure(tmp_path):
    service = pipeline(tmp_path, [
        {'label': 'bus_number', 'box': [75, 10, 100, 30], 'confidence': .9},
        {'label': 'destination', 'box': [10, 10, 70, 30], 'confidence': .85},
        {'label': 'route', 'box': [10, 32, 70, 45], 'confidence': .8}])
    response = service.compare(np.zeros((60, 120, 3), np.uint8), FrameOptions())
    assert service.detector.calls == 1
    engines = {entry['backend']: entry for entry in response['comparisons']}
    assert engines['easyocr']['result']['status'] == 'matched'
    assert engines['paddleocr']['status'] == 'error'
    assert 'private' not in engines['paddleocr']['error']
    assert engines['trocr']['status'] == 'unavailable'
    assert engines['easyocr']['result']['detections'] == response['detections']
    assert any(item['label'] == 'route' for item in response['detections'])
    AnalysisResponse.model_validate(engines['easyocr']['result'])


def test_engine_initialization_failure_does_not_disable_other_engines(tmp_path, monkeypatch):
    from backend.app.services.ocr import registry
    def unavailable(settings):
        raise RuntimeError('missing private model location')
    class Available:
        confidence_method = 'test'
        def __init__(self, settings):
            pass
        def read(self, crop, field):
            return '3', .8
    monkeypatch.setattr(registry, 'EasyOCRAdapter', unavailable)
    monkeypatch.setattr(registry, 'PaddleOCRAdapter', Available)
    monkeypatch.setattr(registry, 'TrOCRAdapter', Available)
    engines = registry.OCRRegistry(Settings(root=tmp_path))
    assert engines.backends() == ['paddleocr', 'trocr']
    assert engines.read(np.zeros((20, 50, 3), np.uint8), 'bus_number', 'trocr') == ('3', .8, 'test')
    assert 'private' not in engines.availability()['easyocr']


def test_low_confidence_text_remains_raw_without_becoming_match(tmp_path):
    from backend.app.services.results import match_fields
    service = pipeline(tmp_path, [])
    fields = {'bus_number': {'raw': '3', 'ocr_confidence': .1},
              'destination': {'raw': 'Tampines Int', 'ocr_confidence': .1}}
    status, match = match_fields(fields, service.matcher, FrameOptions(ocr_threshold=.25))
    assert status == 'unreadable'
    assert match['service'] is None
    assert fields['bus_number']['raw'] == '3'


def test_unknown_reference_and_missing_field_have_distinct_states(tmp_path):
    from backend.app.services.results import match_fields
    service = pipeline(tmp_path, [])
    fields = {'bus_number': {'raw': '999', 'ocr_confidence': .9},
              'destination': {'raw': 'Unknown Destination', 'ocr_confidence': .9}}
    status, match = match_fields(fields, service.matcher, FrameOptions())
    assert status == 'unknown_match' and match['endpoint'] is None
    status, match = match_fields({'bus_number': {'raw': '3', 'ocr_confidence': .9}}, service.matcher, FrameOptions())
    assert status == 'partial' and match['service'] == '3'


class DisplayEngines(Engines):
    def __init__(self, display_text):
        self.display_text, self.display_calls = display_text, 0

    def backends(self):
        return ['easyocr', 'paddleocr']

    def read(self, crop, field, backend):
        return ('', .0, 'test_score') if field == 'destination' else ('3', .9, 'test_score')

    def read_display(self, crop):
        self.display_calls += 1
        return self.display_text, .8, 'pretrained_whole_display_test'


def display_pipeline(tmp_path, fields, display_text):
    service = pipeline(tmp_path, fields)
    service.ocr = DisplayEngines(display_text)
    return service


def test_screen_only_display_uses_pretrained_whole_display_fallback(tmp_path):
    service = display_pipeline(tmp_path, [{'label': 'eds', 'box': [0, 0, 100, 40], 'confidence': .8}], '3\nTAMPINES INT')
    result = service.analyse(np.zeros((60, 120, 3), np.uint8), FrameOptions(backend='paddleocr'))
    parsed = AnalysisResponse.model_validate(result)
    fields = parsed.results[0].fields
    assert parsed.status == 'matched'
    assert {f.ocr_source for f in fields.values()} == {'whole_display_fallback'}
    assert fields['bus_number'].raw == '3' and fields['destination'].raw == 'TAMPINES INT'


def test_fallback_fills_only_unusable_field(tmp_path):
    service = display_pipeline(tmp_path, [
        {'label': 'eds', 'box': [0, 0, 110, 40], 'confidence': .8},
        {'label': 'bus_number', 'box': [75, 10, 100, 30], 'confidence': .9},
        {'label': 'destination', 'box': [10, 10, 70, 30], 'confidence': .85}], '3 TAMPINES INT')
    fields = service.analyse(np.zeros((60, 120, 3), np.uint8), FrameOptions(backend='paddleocr'))['results'][0]['fields']
    assert fields['bus_number'].get('ocr_source', 'field_crop') == 'field_crop'
    assert fields['destination']['ocr_source'] == 'whole_display_fallback'


def test_no_fallback_for_other_engines(tmp_path):
    service = display_pipeline(tmp_path, [{'label': 'eds', 'box': [0, 0, 100, 40], 'confidence': .8}], '3 TAMPINES INT')
    result = service.analyse(np.zeros((60, 120, 3), np.uint8), FrameOptions(backend='easyocr'))
    assert result['status'] == 'unreadable' and service.ocr.display_calls == 0
