import random

from src.models import TierConfig
from src.pitch_generator import generate_pitch_sequence


def _tier1_cfg() -> TierConfig:
    return TierConfig(
        name="Beginner",
        code="T1",
        keys=[{"tonic": "C", "mode": "major"}],
        bar_counts=[1, 2],
        meters=["4/4", "3/4", "2/4"],
        durations_normal=["quarter", "eighth"],
        durations_6_8=[],
        range_semitones_max=12,
        allowed_scale_degrees=[1, 2, 3, 4, 5, 6, 7],
        chromatic_allowed=False,
        chromatic_ratio_max=0.0,
        modal_mixture_allowed=False,
        allowed_intervals_semitones=[1, 2, 3, 4, 5, 7],
        forbidden_intervals=[6, 10, 11],
        max_consecutive_leaps=1,
        leap_compensation_required=True,
        stepwise_ratio_min=0.70,
        start_scale_degrees=[1, 3, 5],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch", "ascending", "descending"],
        leading_tone_resolution_required=True,
        prefer_chord_tones_on_strong_beats=True,
        arch_contour_preference=0.6,
        syncopation_allowed=False,
        tritone_must_resolve_by_step=False,
    )


def test_pitch_sequence_stays_in_global_range_and_is_mostly_stepwise():
    rng = random.Random(1)
    cfg = _tier1_cfg()
    rhythm_durations = ["quarter"] * 16
    contour = [0.5] * len(rhythm_durations)
    pitches = generate_pitch_sequence(
        key_tonic="C",
        key_mode="major",
        contour_targets=contour,
        rhythm_durations=rhythm_durations,
        tier_config=cfg,
        rng=rng,
        starting_pitch=60,  # C4
    )
    assert len(pitches) == 16
    assert all(57 <= p <= 81 for p in pitches)
    intervals = [abs(pitches[i + 1] - pitches[i]) for i in range(len(pitches) - 1)]
    stepwise = sum(1 for x in intervals if x in (1, 2))
    assert stepwise / len(intervals) >= 0.60

