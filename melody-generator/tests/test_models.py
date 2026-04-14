from src.models import Melody, Note, TierConfig


def test_models_construct():
    n = Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1)
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
        notes=[n],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=123,
        template_id="T1_template",
    )
    c = TierConfig(
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
        leap_compensation_required=True,
        stepwise_ratio_min=0.7,
        start_scale_degrees=[1],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch"],
        leading_tone_resolution_required=True,
        prefer_chord_tones_on_strong_beats=True,
        arch_contour_preference=0.6,
        syncopation_allowed=False,
        tritone_must_resolve_by_step=False,
    )
    assert m.notes[0].midi_pitch == 60
    assert c.code == "T1"

