from src.music21_utils import tonic_to_music21


def test_tonic_to_music21_flats():
    assert tonic_to_music21("Bb") == "B-"
    assert tonic_to_music21("Db") == "D-"
    assert tonic_to_music21("Gb") == "G-"


def test_tonic_to_music21_naturals_and_sharps():
    assert tonic_to_music21("C") == "C"
    assert tonic_to_music21("F#") == "F#"

