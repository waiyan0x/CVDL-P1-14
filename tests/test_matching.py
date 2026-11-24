from pathlib import Path
from backend.app.services.matching import RouteMatcher


def test_missing_reference_does_not_disable_detection_or_ocr(tmp_path):
    matcher = RouteMatcher(tmp_path / 'missing.csv')
    result = matcher.match('3', 'Tampines Int', .7)
    assert matcher.available is False
    assert result['status'] == 'unmatched'
    assert result['reason'] == 'Reference data unavailable; raw OCR retained.'


def matcher(tmp_path):
    p = tmp_path / 'routes.csv'
    p.write_text('Route number,Origin,Destination\n65,HarbourFront Int,Tampines Int\n133,Ang Mo Kio Int,Shenton Way Ter\n')
    return RouteMatcher(p)


def test_match_is_constrained_by_service(tmp_path):
    r = matcher(tmp_path).match('65', 'Tamp1nes Int')
    assert r['status'] == 'matched' and r['endpoint'] == 'Tampines Int'
    assert 0.7 <= r['similarity'] < 1


def test_unknown_service_is_not_forced(tmp_path):
    assert matcher(tmp_path).match('13', 'Shenton Way Ter')['status'] == 'unmatched'


def test_no_destination_does_not_invent_one(tmp_path):
    r = matcher(tmp_path).match('65', '')
    assert r['endpoint'] is None and r['status'] == 'service_only'


def test_wrong_destination_is_rejected(tmp_path):
    r = matcher(tmp_path).match('65', 'Woodlands Interchange')
    assert r['endpoint'] is None and r['status'] == 'service_only'


def test_csv_route_identifiers_preserve_letters(tmp_path):
    p = tmp_path / 'routes.csv'
    p.write_text('Route number,Origin,Destination\n2B,A,B\n')
    assert RouteMatcher(p).match('2b', '')['service'] == '2B'


def test_multiline_road_text_does_not_hide_endpoint(tmp_path):
    r = matcher(tmp_path).match('65', 'PUNGGOL RD\nTAMPINES INT')
    assert r['status'] == 'matched' and r['endpoint'] == 'Tampines Int'


def test_split_display_prefers_reference_service_and_keeps_lines(tmp_path):
    service, rest = matcher(tmp_path).split_display('PUNGGOL RD 65\n> Tamp1nes Int')
    assert service == '65' and rest == 'PUNGGOL RD\n> Tamp1nes Int'


def test_split_display_returns_unknown_service_as_read(tmp_path):
    assert matcher(tmp_path).split_display('980 SEMBAWANG') == ('980', 'SEMBAWANG')


def test_split_display_without_service_keeps_all_text(tmp_path):
    assert matcher(tmp_path).split_display('OFF SERVICE') == ('', 'OFF SERVICE')


def test_app_match_fields_passes_route_and_returns_announcement(tmp_path):
    from types import SimpleNamespace
    from backend.app.services.matching import RouteMatcher
    from backend.app.services.results import match_fields
    csv_path = tmp_path / 'bus_information.csv'
    csv_path.write_text('Route number,Origin,Destination\n174,Boon Lay Bus Interchange,Kampong Bahru Bus Terminal\n')
    fields = {'bus_number': {'raw': '174', 'ocr_confidence': .99},
              'destination': {'raw': 'KAMPONG BAHRU TER', 'ocr_confidence': .99},
              'route': {'raw': 'CORPORATION RD', 'ocr_confidence': .99}}
    status, match = match_fields(fields, RouteMatcher(csv_path), SimpleNamespace(ocr_threshold=.25, similarity=.65))
    assert status == 'matched'
    assert match['announcement'] == 'Bus 174 to Kampong Bahru Bus Terminal, via Corporation Rd.'


def test_service_inferred_from_destination_is_reported_with_it(tmp_path):
    # Ang Mo Kio Int is an endpoint of 133 only, so the number is inferred, as the announcement says.
    r = matcher(tmp_path).match('', 'ANG MO KIO INT')
    assert r['status'] == 'matched' and r['service'] == '133' and r['endpoint'] == r['destination'] == 'Ang Mo Kio Int'
    assert r['announcement'] == 'Bus 133 to Ang Mo Kio Int.'


def test_destination_shared_by_services_is_kept_without_a_service(tmp_path):
    p = tmp_path / 'routes.csv'
    p.write_text('Route number,Origin,Destination\n65,HarbourFront Int,Tampines Int\n10,Kent Ridge Ter,Tampines Int\n')
    r = RouteMatcher(p).match('', 'TAMPINES INT')
    assert r['status'] == 'unmatched' and r['service'] is None and r['endpoint'] is None
    assert r['destination'] == 'Tampines Int'
    assert r['announcement'].startswith('A bus to Tampines Int is approaching.')
