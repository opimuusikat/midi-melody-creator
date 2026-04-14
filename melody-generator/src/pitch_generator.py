from __future__ import annotations

"""
Pitch generation using constrained stochastic selection.

This module deliberately starts modest: it can generate a pitch sequence biased
toward stepwise motion and staying in-key, while respecting the global A3..A5
range and tier interval constraints.

More advanced musical rules (chromatic quotas, leading-tone enforcement, leap
compensation, etc.) are validated later by `validator.py` and can be pushed into
generation iteratively.
"""

from dataclasses import dataclass
from typing import Iterable

import math

import numpy as np
from music21 import key as m21key
from music21 import pitch as m21pitch

from src.models import TierConfig


MIN_MIDI = 57  # A3
MAX_MIDI = 81  # A5


INTERVAL_WEIGHTS_STEPWISE: dict[int, float] = {
    0: 0.1,
    1: 3.0,
    2: 3.0,
    3: 1.5,
    4: 1.5,
    5: 1.0,
    6: 0.2,
    7: 1.0,
    8: 0.4,
    9: 0.5,
    10: 0.2,
    11: 0.2,
    12: 0.6,
}


def _key_scale_midi_set(key_tonic: str, key_mode: str) -> set[int]:
    """
    Return a set of allowed MIDI pitches for the key across the global range.

    For v1 we treat modes as "diatonic collections" via music21 Key/Scale
    conveniences; this is a pragmatic start that keeps generation stable.
    """

    # music21 Key can represent major/minor cleanly; for other modes we fallback
    # to Key + mode string if possible.
    k = m21key.Key(key_tonic, key_mode)
    pitch_classes = {p.pitchClass for p in k.getPitches()}

    allowed: set[int] = set()
    for midi in range(MIN_MIDI, MAX_MIDI + 1):
        p = m21pitch.Pitch()
        p.midi = midi
        if p.pitchClass in pitch_classes:
            allowed.add(midi)
    return allowed


def _gaussian_weight(actual: float, target: float, sigma: float) -> float:
    if sigma <= 0:
        return 1.0
    return math.exp(-((actual - target) ** 2) / (2.0 * sigma * sigma))


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _contour_target_to_midi(target: float, center: float = 69.0, span: float = 12.0) -> float:
    """
    Map contour target in [0,1] to a MIDI target around `center` with `span`.
    """
    t = _clamp(float(target), 0.0, 1.0)
    return (center - span / 2.0) + t * span


def _candidate_pitches(
    prev_pitch: int, allowed_in_key: set[int], tier_config: TierConfig
) -> list[int]:
    candidates: list[int] = []
    for midi in range(MIN_MIDI, MAX_MIDI + 1):
        if midi not in allowed_in_key:
            continue

        interval = abs(midi - prev_pitch)
        if interval == 0:
            continue
        if interval in tier_config.forbidden_intervals:
            continue
        if tier_config.allowed_intervals_semitones and interval not in tier_config.allowed_intervals_semitones:
            continue
        candidates.append(midi)
    return candidates


def generate_pitch_sequence(
    *,
    key_tonic: str,
    key_mode: str,
    contour_targets: list[float],
    rhythm_durations: list[str],
    tier_config: TierConfig,
    rng,
    starting_pitch: int,
) -> list[int]:
    if len(contour_targets) != len(rhythm_durations):
        raise ValueError("contour_targets and rhythm_durations must be the same length")
    if not (MIN_MIDI <= starting_pitch <= MAX_MIDI):
        raise ValueError("starting_pitch must be within global range")
    if not contour_targets:
        return []

    allowed_in_key = _key_scale_midi_set(key_tonic, key_mode)

    pitches: list[int] = [starting_pitch]

    sigma = 4.5  # moderately strong contour pull
    for i in range(1, len(contour_targets)):
        prev = pitches[-1]
        candidates = _candidate_pitches(prev, allowed_in_key, tier_config)
        if not candidates:
            # last resort: stay still (should be caught by validator later)
            pitches.append(prev)
            continue

        target_midi = _contour_target_to_midi(contour_targets[i])

        weights: list[float] = []
        for c in candidates:
            interval = abs(c - prev)
            interval_w = INTERVAL_WEIGHTS_STEPWISE.get(interval, 0.2)
            contour_w = _gaussian_weight(float(c), target_midi, sigma=sigma)
            w = max(1e-9, interval_w * contour_w)
            weights.append(w)

        choice = rng.choices(candidates, weights=weights, k=1)[0]
        pitches.append(choice)

    return pitches

