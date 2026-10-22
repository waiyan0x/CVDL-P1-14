from backend.app.services.association import associate_displays


def field(label, box, confidence=.9):
    return {'label': label, 'box': box, 'confidence': confidence, 'source': 'model'}


def test_fields_never_pair_across_known_screen_owners():
    groups, detections = associate_displays([
        field('eds', [0, 0, 100, 40]), field('eds', [110, 0, 210, 40]),
        field('bus_number', [70, 10, 95, 30]),
        field('destination', [115, 10, 170, 30]),
    ], 220, 50)
    assert len(groups) == 2
    assert list(groups[0]['fields']) == ['bus_number']
    assert list(groups[1]['fields']) == ['destination']
    assert all(d['display_id'] for d in detections)


def test_screen_only_detection_remains_a_group():
    groups, _ = associate_displays([field('eds', [0, 0, 100, 40])], 100, 40)
    assert len(groups) == 1
    assert groups[0]['fields'] == {}
    assert groups[0]['screen']['source'] == 'model'


def test_unowned_paired_fields_create_estimate_without_confidence():
    groups, detections = associate_displays([
        field('destination', [0, 0, 70, 25]), field('bus_number', [75, 0, 100, 30])
    ], 100, 40)
    assert len(groups) == 1
    assert groups[0]['screen']['box'] == [0, 0, 100, 40]
    assert groups[0]['screen']['confidence'] is None
    assert groups[0]['screen']['source'] == 'field_union'
    assert len({d['id'] for d in detections}) == 3


def test_separate_vertical_displays_do_not_pair():
    groups, _ = associate_displays([
        field('bus_number', [75, 10, 100, 30]), field('destination', [10, 100, 70, 130])
    ], 200, 200)
    assert len(groups) == 2
    assert all(group['screen'] is None for group in groups)
