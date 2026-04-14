from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any


def _frozen_dataclass(*, slots: bool = True):
    """
    Compatibility wrapper for dataclass(slots=...).

    - Python 3.10+: supports frozen+slots
    - Python 3.9: slots not supported, so we fall back to frozen-only
    """

    if slots and sys.version_info >= (3, 10):
        return dataclass(frozen=True, slots=True)
    return dataclass(frozen=True)


@_frozen_dataclass()
class Note:
    """A single note in a melody."""

    midi_pitch: int  # 57..81 (A3..A5)
    duration: str  # "whole", "half", "quarter", "eighth", ...
    beat_position: float  # position within the bar in quarter-note units
    bar_number: int  # 1-indexed


@_frozen_dataclass()
class Melody:
    """A complete generated melody."""

    melody_id: str  # e.g. "T1_Cmaj_44_2bar_arch_0001"
    notes: list[Note]
    tier: int  # 1, 2, or 3
    key_tonic: str  # "C", "G", etc.
    key_mode: str  # "major", "minor", "dorian", etc.
    meter: str  # "4/4", "3/4", "2/4"
    bar_count: int
    contour_type: str
    cadence_type: str
    seed: int  # random seed used to generate this melody
    template_id: str  # which template was used


@_frozen_dataclass()
class TierConfig:
    """Loaded from YAML — all rules for one tier."""

    name: str
    code: str
    keys: list[dict[str, Any]]
    bar_counts: list[int]
    meters: list[str]
    durations_normal: list[str]
    durations_6_8: list[str]

    # Pitch rules
    range_semitones_max: int
    allowed_scale_degrees: list[int]
    chromatic_allowed: bool
    chromatic_ratio_max: float
    modal_mixture_allowed: bool

    # Interval rules
    allowed_intervals_semitones: list[int]
    forbidden_intervals: list[int]
    max_consecutive_leaps: int
    leap_compensation_required: bool
    stepwise_ratio_min: float

    # Structural rules
    start_scale_degrees: list[int]
    end_scale_degrees: list[int]
    cadence_types: list[str]
    contour_types: list[str]
    leading_tone_resolution_required: bool

    # Soft weighting / additional allowances (tier-specific, optional)
    prefer_chord_tones_on_strong_beats: bool = False
    arch_contour_preference: float = 0.0
    syncopation_allowed: bool = False
    tritone_must_resolve_by_step: bool = False

    # Student-usefulness constraints (tier-specific, optional)
    max_notes_per_beat: float | None = None
    max_notes_per_bar: int | None = None
    require_stepwise_final_approach: bool = False


