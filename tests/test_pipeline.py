from demo.pipeline import pair_fields


def field(label, box, confidence=.9):
    return {'label': label, 'box': box, 'confidence': confidence}


def test_multiple_bus_fields_are_not_crossed():
    left = field('destination', [10, 10, 70, 30])
    right = field('destination', [310, 10, 370, 30])
    numbers = [field('bus_number', [75, 10, 100, 30]), field('bus_number', [375, 10, 400, 30])]
    groups = pair_fields([left, right, *numbers])
    assert groups[0][1] == left and groups[1][1] == right


def test_unrelated_vertical_regions_remain_separate():
    groups = pair_fields([field('bus_number', [75, 10, 100, 30]), field('destination', [10, 100, 70, 130])])
    assert groups[0][1] is None and groups[1][0] is None


def test_missing_number_is_retained_for_raw_ocr():
    d = field('destination', [10, 10, 70, 30])
    assert pair_fields([d]) == [(None, d)]
