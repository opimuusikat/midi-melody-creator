from pathlib import Path

from src.config_loader import load_tier_config


def test_tierconfig_has_defaults_for_new_fields():
    # If TierConfig adds fields, existing YAMLs must still load without specifying them.
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "tier2.yaml"
    cfg = load_tier_config(cfg_path)

    assert cfg.max_notes_per_beat is None
    assert cfg.max_notes_per_bar is None
    assert cfg.require_stepwise_final_approach is False


def test_validator_rejects_non_stepwise_final_approach_when_required():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(require_stepwise_final_approach=True)
    # Ends on tonic (C) but approaches by a leap (G->C is 5 semitones).
    notes = [
        Note(midi_pitch=67, duration="quarter", beat_position=0.0, bar_number=1),  # G4
        Note(midi_pitch=72, duration="quarter", beat_position=1.0, bar_number=1),  # C5
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
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
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("final approach" in v.lower() for v in violations)


def test_validator_rejects_too_dense_when_max_notes_per_beat_set():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(max_notes_per_beat=1.0)
    # 4/4, 1 bar => 4 beats. 6 notes => 1.5 notes/beat (too dense).
    notes = [
        Note(midi_pitch=60, duration="eighth", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="eighth", beat_position=0.5, bar_number=1),
        Note(midi_pitch=64, duration="eighth", beat_position=1.0, bar_number=1),
        Note(midi_pitch=65, duration="eighth", beat_position=1.5, bar_number=1),
        Note(midi_pitch=67, duration="eighth", beat_position=2.0, bar_number=1),
        Note(midi_pitch=60, duration="eighth", beat_position=2.5, bar_number=1),
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0002",
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
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any(("density" in v.lower()) or ("notes per beat" in v.lower()) for v in violations)


def test_validator_rejects_too_dense_when_max_notes_per_bar_set():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(max_notes_per_bar=4)
    # 1 bar => 6 notes => 6 notes/bar (too dense).
    notes = [
        Note(midi_pitch=60, duration="eighth", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="eighth", beat_position=0.5, bar_number=1),
        Note(midi_pitch=64, duration="eighth", beat_position=1.0, bar_number=1),
        Note(midi_pitch=65, duration="eighth", beat_position=1.5, bar_number=1),
        Note(midi_pitch=67, duration="eighth", beat_position=2.0, bar_number=1),
        Note(midi_pitch=60, duration="eighth", beat_position=2.5, bar_number=1),
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0003",
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
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any(("density" in v.lower()) or ("notes per bar" in v.lower()) for v in violations)


def test_validator_reports_unsupported_meter_when_max_notes_per_beat_set():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(max_notes_per_beat=1.0)
    notes = [
        Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
    ]
    m = Melody(
        melody_id="T1_Cmaj_54_1bar_arch_0004",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="5/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("Unsupported meter" in v for v in violations)


def test_validator_reports_invalid_bar_count_when_max_notes_per_beat_set():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(max_notes_per_beat=1.0)
    notes = [
        Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_0bar_arch_0005",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=0,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("Invalid bar_count" in v for v in violations)


def test_validator_reports_invalid_bar_count_when_max_notes_per_bar_set():
    from src.models import Melody, Note, TierConfig
    from src.validator import validate_melody

    def _mk_tier(**overrides):
        base = dict(
            name="Beginner",
            code="T1",
            keys=[{"tonic": "C", "mode": "major"}],
            bar_counts=[1],
            meters=["4/4"],
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
            stepwise_ratio_min=0.0,
            start_scale_degrees=[1, 3, 5],
            end_scale_degrees=[1],
            cadence_types=["authentic"],
            contour_types=["arch"],
            leading_tone_resolution_required=True,
        )
        base.update(overrides)
        return TierConfig(**base)

    tier = _mk_tier(max_notes_per_bar=4)
    notes = [
        Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),  # C4
        Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),  # D4
        Note(midi_pitch=60, duration="quarter", beat_position=2.0, bar_number=1),  # C4
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_0bar_arch_0006",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=0,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("Invalid bar_count" in v for v in violations)
    assert any("notes per bar" in v.lower() for v in violations)
