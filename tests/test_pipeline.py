"""Original field/envelope regression cases migrated to screen ownership."""
from backend.app.services.association import associate_displays


def field(label, box, confidence=.9):
    return {'label': label, 'box': box, 'confidence': confidence}


def groups(fields, width=500, height=200):
    return associate_displays(fields, width, height)[0]


def test_multiple_bus_fields_are_not_crossed():
    results = groups([field('destination', [10, 10, 70, 30]), field('destination', [310, 10, 370, 30]),
                      field('bus_number', [75, 10, 100, 30]), field('bus_number', [375, 10, 400, 30])])
    assert len(results) == 2
    assert results[0]['fields']['destination']['box'] == [10, 10, 70, 30]
    assert results[1]['fields']['destination']['box'] == [310, 10, 370, 30]


def test_unrelated_vertical_regions_remain_separate():
    results = groups([field('bus_number', [75, 10, 100, 30]), field('destination', [10, 100, 70, 130])])
    assert len(results) == 2
    assert list(results[0]['fields']) == ['bus_number']
    assert list(results[1]['fields']) == ['destination']


def test_missing_number_is_retained_for_raw_ocr():
    results = groups([field('destination', [10, 10, 70, 30])])
    assert len(results) == 1
    assert results[0]['fields']['destination']['box'] == [10, 10, 70, 30]


def test_eds_envelope_contains_both_fields_and_clips_to_image():
    result = groups([field('destination', [0, 0, 70, 25]), field('bus_number', [75, 0, 100, 30])], 100, 40)[0]
    assert result['screen']['box'] == [0, 0, 100, 40]
    assert result['screen']['source'] == 'field_union'
    assert result['screen']['confidence'] is None


def test_model_screen_is_not_duplicated():
    results = groups([field('destination', [10, 10, 70, 30]), field('bus_number', [75, 10, 100, 30]),
                      field('eds', [0, 0, 110, 40])])
    assert len(results) == 1
    assert results[0]['screen']['source'] == 'model'


def test_two_displays_keep_separate_envelopes():
    results = groups([field('destination', [10, 10, 70, 30]), field('bus_number', [75, 10, 100, 30]),
                      field('destination', [310, 10, 370, 30]), field('bus_number', [375, 10, 400, 30])])
    assert results[0]['screen']['box'][2] < results[1]['screen']['box'][0]


def test_one_field_does_not_claim_a_whole_screen():
    assert groups([field('bus_number', [75, 10, 100, 30])])[0]['screen'] is None
