from src.models import Melody, Note, TierConfig
from src.validator import validate_melody


def _cfg() -> TierConfig:
    return TierConfig(
        name="Beginner",
        code="T1",
        keys=[{"tonic": "C", "mode": "major"}],
        bar_counts=[1],
        meters=["4/4"],
        durations_normal=["quarter"],
        durations_6_8=[],
        range_semitones_max=12,
        allowed_scale_degrees=[1, 2, 3, 4, 5, 6, 7],
        chromatic_allowed=False,
        chromatic_ratio_max=0.0,
        modal_mixture_allowed=False,
        allowed_intervals_semitones=[1, 2],
        forbidden_intervals=[],
        max_consecutive_leaps=1,
        leap_compensation_required=False,
        stepwise_ratio_min=0.5,
        start_scale_degrees=[1],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch"],
        leading_tone_resolution_required=False,
        prefer_chord_tones_on_strong_beats=False,
        arch_contour_preference=0.0,
        syncopation_allowed=False,
        tritone_must_resolve_by_step=False,
    )


def test_validator_rejects_out_of_range_pitch():
    cfg = _cfg()
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=56, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=60, duration="quarter", beat_position=1.0, bar_number=1),
        ],
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
    passed, violations = validate_melody(m, cfg)
    assert passed is False
    assert any("range" in v.lower() for v in violations)


def test_validator_accepts_simple_valid_melody():
    cfg = _cfg()
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
            Note(midi_pitch=60, duration="quarter", beat_position=2.0, bar_number=1),
        ],
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
    passed, violations = validate_melody(m, cfg)
    assert passed is True
    assert violations == []

