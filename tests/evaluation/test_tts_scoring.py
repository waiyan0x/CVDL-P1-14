import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'score_tts_transcripts', Path(__file__).resolve().parents[2] / 'scripts/score_tts_transcripts.py')
scoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)

REFERENCE = 'Bus 9 2 B to Pasir Ris Drive 12, Block 7 4 7 A.'


def test_spelled_and_written_codes_normalise_alike():
    assert scoring.normalise('Bus 9 2 B to') == scoring.normalise('Bus 92B to') == ['bus', '92b', 'to']
    assert scoring.normalise('Bedok M R T station') == scoring.normalise('Bedok MRT station')
    assert scoring.normalise('Block seven four seven A') == ['block', '747a']


def test_hyphenated_codes_join_but_hyphenated_names_split():
    assert scoring.normalise('Bus TS-1 to') == scoring.normalise('Bus T S 1 to') == ['bus', 'ts1', 'to']
    assert scoring.normalise('Bus 8-4G to') == ['bus', '84g', 'to']
    assert scoring.normalise('opposite the Ritz-Carlton') == ['opposite', 'the', 'ritz', 'carlton']


def test_us_spelling_matches_reference_spelling():
    assert scoring.normalise('Woodlands Center Road') == scoring.normalise('Woodlands Centre Road')


def test_perfect_transcript_scores_zero_errors():
    result = scoring.score(REFERENCE, 'Bus 92B to Pasir Ris Drive 12, Block 747A.', '92B')
    assert result['word_errors'] == 0 and result['service_correct'] == 1 and result['dest_exact'] == 1


def test_misheard_service_and_abbreviation_are_counted():
    result = scoring.score(REFERENCE, 'Bus 92 to Pasir Ris Drive 12, Blick 747A.', '92B')
    assert result['service_correct'] == 0
    assert result['dest_errors'] == 1 and result['dest_exact'] == 0
    assert result['word_errors'] == 2


def test_to_heard_as_two_counts_against_the_service_only():
    # "9 2 B to" heard as "92B2": the service is wrong, the destination is still found.
    result = scoring.score(REFERENCE, 'Bus 92B2 Pasir Ris Drive 12, Block 747A.', '92B')
    assert result['service_correct'] == 0 and result['dest_exact'] == 1
