from src.difficulty_scorer import score_melody
from src.models import Melody, Note


def test_difficulty_score_is_numeric_and_has_subscores():
    notes = [
        Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
        Note(midi_pitch=64, duration="quarter", beat_position=2.0, bar_number=1),
        Note(midi_pitch=65, duration="quarter", beat_position=3.0, bar_number=1),
    ]
    m = Melody(
        melody_id="x",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    composite, subs = score_melody(m)
    assert isinstance(composite, float)
    assert "interval_difficulty" in subs

