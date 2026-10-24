"""Per-frame screen ownership, field pairing and honest estimated envelopes."""
from copy import deepcopy


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def intersection(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def pairing_cost(number, destination):
    x1, y1, x2, y2 = number['box']
    a, b, c, d = destination['box']
    height = max(1, y2 - y1)
    overlap = max(0, min(y2, d) - max(y1, b)) / max(1, min(height, d - b))
    gap = max(0, max(x1, a) - min(x2, c))
    if overlap < .25 or gap > 8 * height:
        return None
    return gap / height + abs((y1 + y2 - b - d) / 2) / height * 3


def pair_leftovers(fields):
    """Choose valid edges in increasing geometry cost without reusing either field."""
    numbers = [field for field in fields if field['label'] == 'bus_number']
    destinations = [field for field in fields if field['label'] == 'destination']
    edges = []
    for number in numbers:
        for destination in destinations:
            cost = pairing_cost(number, destination)
            if cost is not None:
                edges.append((cost, number['id'], destination['id'], number, destination))
    used, pairs = set(), []
    for _, number_id, destination_id, number, destination in sorted(edges, key=lambda edge: edge[:3]):
        if number_id not in used and destination_id not in used:
            pairs.append({'bus_number': number, 'destination': destination})
            used.update((number_id, destination_id))
    pairs.extend({field['label']: field} for field in fields if field['id'] not in used)
    return pairs


def estimated_screen(fields, width, height):
    if len(fields) < 2:
        return None
    boxes = [field['box'] for field in fields.values()]
    x1, y1 = min(box[0] for box in boxes), min(box[1] for box in boxes)
    x2, y2 = max(box[2] for box in boxes), max(box[3] for box in boxes)
    dx, dy = max(4, round((x2 - x1) * .15)), max(4, round((y2 - y1) * .35))
    return {'label': 'eds', 'box': [max(0, x1 - dx), max(0, y1 - dy), min(width, x2 + dx), min(height, y2 + dy)],
            'confidence': None, 'source': 'field_union'}


def associate_displays(predictions, width, height):
    """Return groups and labelled detections; identities are scoped to one frame."""
    detections = deepcopy(predictions)
    for index, field in enumerate(detections, 1):
        field.update(id=f'field-{index}', source=field.get('source', 'model'))
    screens = [field for field in detections if field['label'] == 'eds']
    fields = [field for field in detections if field['label'] in ('bus_number', 'destination')]
    owners = {screen['id']: [] for screen in screens}
    unowned = []
    for field in fields:
        choices = [screen for screen in screens if intersection(field['box'], screen['box']) / max(1, area(field['box'])) >= .7]
        if choices:
            owner = min(choices, key=lambda screen: area(screen['box']))
            owners[owner['id']].append(field)
        else:
            unowned.append(field)
    groups = []
    for screen in screens:
        owned = owners[screen['id']]
        # One text field per label per EDS. Duplicate detector outputs remain visible,
        # but cannot steal a field from a neighbouring known screen.
        selected = {}
        for field in sorted(owned, key=lambda field: -field['confidence']):
            selected.setdefault(field['label'], field)
        groups.append({'screen': screen, 'fields': selected, 'owned': owned})
    for pair in pair_leftovers(unowned):
        screen = estimated_screen(pair, width, height)
        if screen:
            screen['id'] = f'field-{len(detections) + 1}'
            detections.append(screen)
        groups.append({'screen': screen, 'fields': pair, 'owned': list(pair.values())})
    groups.sort(key=lambda group: tuple((group['screen'] or next(iter(group['fields'].values())))['box'][1::-1]))
    for index, group in enumerate(groups, 1):
        display_id = f'display-{index}'
        group['display_id'] = display_id
        for field in group.pop('owned') + ([group['screen']] if group['screen'] else []):
            field['display_id'] = display_id
    return groups, detections
