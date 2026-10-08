from demo.pipeline import pair_fields, add_eds_boxes


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


def test_eds_envelope_contains_both_fields_and_clips_to_image():
    fields = [field('destination', [0, 0, 70, 25]), field('bus_number', [75, 0, 100, 30])]
    screen = add_eds_boxes(fields, pair_fields(fields), 100, 40)[-1]
    assert screen['box'] == [0, 0, 100, 40]
    assert screen['source'] == 'field_union' and screen['confidence'] is None


def test_model_screen_is_not_duplicated():
    fields = [field('destination', [10, 10, 70, 30]), field('bus_number', [75, 10, 100, 30]),
              field('eds', [0, 0, 110, 40])]
    assert add_eds_boxes(fields, pair_fields(fields), 200, 100) == fields


def test_two_displays_keep_separate_envelopes():
    fields = [field('destination', [10, 10, 70, 30]), field('bus_number', [75, 10, 100, 30]),
              field('destination', [310, 10, 370, 30]), field('bus_number', [375, 10, 400, 30])]
    screens = add_eds_boxes(fields, pair_fields(fields), 500, 100)[-2:]
    assert screens[0]['box'][2] < screens[1]['box'][0]


def test_one_field_does_not_claim_a_whole_screen():
    fields = [field('bus_number', [75, 10, 100, 30])]
    assert add_eds_boxes(fields, pair_fields(fields), 200, 100) == fields
