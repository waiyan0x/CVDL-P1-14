"""Decision rules of the reference matcher on a small synthetic reference."""
import pytest

from backend.app.services.reference_matching import (
    DisplayMatcher, Reference, Settings, normalise_place, normalise_service, load_abbreviations)

CSV = """Route number,Origin,Destination
65,HarbourFront Bus Interchange,Tampines Bus Interchange
14E,Bedok Bus Interchange,Clementi Bus Interchange
148,Toa Payoh Bus Interchange,Bukit Merah Bus Interchange
30,Bedok Bus Interchange,Boon Lay Bus Interchange
30,Bedok Bus Interchange,Boon Lay Bus Interchange
88,Pasir Ris Bus Interchange,Pasir Ris Bus Interchange (loop)
901,Woodlands Bus Interchange,Woodlands Centre Road (loop)
222,Bedok North Avenue 3,Bedok North Street 3
"""


@pytest.fixture()
def matcher(tmp_path):
    path = tmp_path / "routes.csv"
    path.write_text(CSV)
    return DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio"))


def test_normalisation_shares_one_form_for_both_sides():
    abbrev = load_abbreviations()
    assert normalise_place("> TOA PAYOH INT", abbrev) == normalise_place("Toa Payoh Bus Interchange", abbrev, display=False)
    assert normalise_place("WOODLANDS INT VIA UPP THOMSON", abbrev) == "WOODLANDS INT"
    assert normalise_place("WDL INT/MRT", abbrev) == "WOODLANDS INT MRT"
    assert normalise_service(" 14e ") == "14E" and normalise_service("070") == "070"


def test_exact_duplicate_rows_are_dropped(matcher):
    assert len(matcher.reference.services["30"]) == 1


def test_number_and_destination_matched(matcher):
    r = matcher.match(number="65", destination="TAMP1NES INT")
    assert r["status"] == "matched" and r["service"] == "65"
    assert r["destination"] == "Tampines Bus Interchange" and 70 <= r["destination_score"] < 100
    assert r["raw"]["destination"] == "TAMP1NES INT"


def test_number_only_never_guesses_direction(matcher):
    r = matcher.match(number="30")
    assert r["status"] == "service_only" and r["destination"] is None


def test_number_only_infers_destination_for_single_endpoint_loop(matcher):
    r = matcher.match(number="88")
    assert r["status"] == "matched" and r["destination_status"] == "inferred"


def test_number_suffix_is_never_dropped(matcher):
    assert matcher.match(number="14")["status"] == "unable_to_detect"
    assert matcher.match(number="14E")["service"] == "14E"


def test_service_missing_from_reference_is_unable_to_detect(matcher):
    r = matcher.match(number="147E")
    assert r["status"] == "unable_to_detect" and r["service"] is None


def test_valid_but_wrong_number_conflicts_with_destination(matcher):
    # 14E misread as 148: 148 is real, but the destination belongs to 14E.
    r = matcher.match(number="148", destination="CLEMENTI INT")
    assert r["status"] == "conflict" and r["service"] is None and r["destination"] is None


def test_destination_only_infers_number_when_unique(matcher):
    r = matcher.match(destination="TAMPINES INT")
    assert r["status"] == "matched" and r["service"] == "65" and r["service_status"] == "inferred"


def test_destination_only_shared_by_services_keeps_number_open(matcher):
    r = matcher.match(destination="BEDOK INT")
    assert r["status"] == "destination_only" and r["service"] is None
    assert r["destination"] == "Bedok Bus Interchange"


def test_similar_names_tie_instead_of_guessing(matcher):
    # Avenue 3 and Street 3 differ by one word; a garbled read must not pick one.
    r = matcher.match(destination="BEDOK NTH A 3")
    assert r["destination"] is None


def test_tied_destinations_sharing_one_service_resolve_the_number(matcher):
    r = matcher.match(destination="BEDOK NTH A 3")
    assert r["service"] == "222" and r["status"] == "service_only"


def test_wrong_destination_below_cutoff_stays_unresolved(matcher):
    r = matcher.match(number="65", destination="SENGKANG INT")
    assert r["status"] == "service_only" and r["destination"] is None
    assert r["destination_status"] == "below_cutoff"


def test_depot_message_is_not_matched(matcher):
    assert matcher.match(number="30", destination="> BEDOK NTH DEPOT")["status"] == "not_in_service"


def test_route_text_only_is_kept(matcher):
    r = matcher.match(route="UPP THOMSON RD")
    assert r["status"] == "route_text_only" and r["route_text"] == "UPP THOMSON RD"


def test_no_fields_and_unreadable(matcher):
    assert matcher.match(detected=False)["status"] == "no_fields"
    assert matcher.match(number="", destination="")["status"] == "unreadable"


def test_whole_display_only_is_number_and_destination(matcher):
    r = matcher.match(panel="65 TAMPINES INT")
    assert r["status"] == "matched" and r["service"] == "65"
    assert r["sources"] == {"service": ["panel"], "destination": ["panel"]}


def test_crop_and_panel_agreement_logs_both_sources(matcher):
    r = matcher.match(number="65", destination="TAMPINES INT", panel="65 TAMPINES INT")
    assert r["sources"]["service"] == ["crop", "panel"]


def test_crop_and_panel_disagreement_resolved_by_destination(matcher):
    r = matcher.match(number="148", destination="CLEMENTI INT", panel="14E CLEMENTI")
    assert r["service"] == "14E" and r["status"] == "matched"


def test_crop_and_panel_disagreement_without_evidence_is_unresolved(matcher):
    r = matcher.match(number="148", panel="14E")
    assert r["status"] == "unresolved" and r["service_status"] == "disputed"


def test_partial_panel_number_does_not_dispute_crop(matcher):
    # Whole-display OCR often drops a digit (110 -> 10); that is not a second plausible number.
    r = matcher.match(number="148", panel="TOA PAYOH 14")
    assert r["service"] == "148" and r["service_status"] == "accepted"


def test_panel_number_never_replaces_a_number_missing_from_reference(matcher):
    r = matcher.match(number="350", panel="o 30")
    assert r["status"] == "unable_to_detect" and r["service"] is None


def test_conflict_policy_keep_number(tmp_path):
    path = tmp_path / "routes.csv"
    path.write_text(CSV)
    m = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio", conflict="keep_number"))
    r = m.match(number="148", destination="CLEMENTI INT")
    assert r["status"] == "conflict" and r["service"] == "148" and r["destination"] is None


def test_cli_reads_crops_before_matching(monkeypatch, capsys, tmp_path):
    import importlib.util, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("match_reference", root / "scripts/match_reference.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    fake = {"num.png": ("983", 0.99), "dest.png": ("CHOA CHU KANG INT", 0.95)}
    monkeypatch.setattr(cli, "make_reader", lambda model_dir=None: lambda path: fake[Path(path).name])
    monkeypatch.setattr(cli, "resolve_ocr_dir", lambda model_dir: None)   # ignore weights in models/local
    cli.main(["--number-crop", str(tmp_path / "num.png"), "--destination-crop", str(tmp_path / "dest.png")])
    out = capsys.readouterr().out
    assert "public pretrained" in out and "'983'" in out
    assert "MATCHED" in out and "Choa Chu Kang Bus Interchange" in out


def test_photo_mode_drops_duplicate_display_boxes():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("match_reference", Path(__file__).resolve().parents[1] / "scripts/match_reference.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    boxes = [{"label": "eds", "confidence": 0.9, "box": [488, 677, 649, 722]},
             {"label": "eds", "confidence": 0.53, "box": [432, 687, 636, 719]},
             {"label": "bus_number", "confidence": 0.8, "box": [490, 683, 531, 718]}]
    kept = cli.drop_duplicate_panels(boxes)
    assert [b["confidence"] for b in kept] == [0.9, 0.8]


def test_route_crop_as_destination_fallback(tmp_path):
    path = tmp_path / "routes.csv"
    path.write_text(CSV)
    off = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio"))
    on = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio", route_as_destination="use"))
    check = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio", route_as_destination="check"))
    assert check.match(number="65", route="TAMPINES INT")["destination"] is None      # never shown in check mode
    assert check.match(number="148", route="CLEMENTI INT")["status"] == "conflict"    # but still flags the number
    assert check.match(number="65", route="TAMPINES INT")["status"] == "service_only"
    assert off.match(number="65", route="TAMPINES INT")["destination"] is None
    r = on.match(number="65", route="TAMPINES INT")
    assert r["destination"] == "Tampines Bus Interchange" and r["sources"]["destination"] == ["route"]
    assert r["route_text"] == "TAMPINES INT"
    # A wrong but valid number is now caught by the route-crop destination.
    assert on.match(number="148", route="CLEMENTI INT")["status"] == "conflict"
    # A real destination crop always wins over the route crop.
    assert on.match(number="65", destination="TAMPINES INT", route="UPP THOMSON RD")["sources"]["destination"] == ["crop"]


def test_route_text_that_is_another_endpoint_does_not_block_the_panel(tmp_path):
    # Real route text can name another service's endpoint (374 photo: ANCHORVALE RD);
    # the whole display still gives this service's destination.
    path = tmp_path / "routes.csv"
    path.write_text(CSV)
    on = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=5, scorer="ratio", route_as_destination=True))
    r = on.match(number="65", route="CLEMENTI INT", panel="65 TAMPINES INT")
    assert r["status"] == "matched" and r["destination"] == "Tampines Bus Interchange"
    assert r["sources"]["destination"] == ["panel"]


def test_photo_mode_attaches_a_lone_line_to_the_display_below_it():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("match_reference", Path(__file__).resolve().parents[1] / "scripts/match_reference.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    main = {"screen": None, "display_id": "display-1",
            "fields": {"bus_number": {"box": [280, 30, 360, 75]}, "destination": {"box": [95, 60, 270, 80]}}}
    lone = {"screen": None, "display_id": "display-2", "fields": {"route": {"box": [95, 38, 265, 58]}}}
    far = {"screen": None, "display_id": "display-3", "fields": {"route": {"box": [95, 400, 265, 420]}}}
    kept = cli.merge_orphan_lines([main, lone, far])
    assert set(kept[0]["fields"]) == {"bus_number", "destination", "route"}
    assert far in kept and lone not in kept


def test_number_missing_from_reference_with_route_text_is_unable_to_detect(tmp_path):
    path = tmp_path / "routes.csv"
    path.write_text(CSV)
    m = DisplayMatcher(Reference(path), Settings(cutoff=70, margin=10, scorer="ratio", route_as_destination="check"))
    r = m.match(number="1", route="ANG ND KIG TT")
    assert r["status"] == "unable_to_detect" and r["service_status"] == "not_in_reference"
    assert r["route_text"] == "ANG ND KIG TT"
