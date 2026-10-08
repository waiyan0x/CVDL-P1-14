from pathlib import Path
from demo.matching import RouteMatcher


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
