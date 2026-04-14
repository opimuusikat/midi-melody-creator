from __future__ import annotations

"""
Hard-rule validation for generated melodies.

This module enforces the non-negotiable constraints (range, interval legality,
stepwise ratio thresholds, etc.). Generation can be imperfect; the validator is
the final gate before accepting a melody into the corpus.
"""

from music21 import key as m21key
from music21 import pitch as m21pitch

from src.models import Melody, TierConfig
from src.pitch_generator import MAX_MIDI, MIN_MIDI


def _scale_degree(key_tonic: str, key_mode: str, midi_pitch: int) -> int:
    k = m21key.Key(key_tonic, key_mode)
    p = m21pitch.Pitch()
    p.midi = midi_pitch
    deg = k.getScaleDegreeFromPitch(p)
    if deg is None:
        # Chromatic pitch (or mode mismatch)
        return 0
    return int(deg)


def validate_melody(melody: Melody, tier_config: TierConfig) -> tuple[bool, list[str]]:
    violations: list[str] = []

    if not melody.notes:
        violations.append("Melody has no notes.")
        return False, violations

    pitches = [n.midi_pitch for n in melody.notes]

    # 1. Global pitch range
    if any(p < MIN_MIDI or p > MAX_MIDI for p in pitches):
        violations.append(f"Pitch out of global range {MIN_MIDI}..{MAX_MIDI}.")

    # 2. Range within melody
    mel_range = max(pitches) - min(pitches)
    if mel_range > tier_config.range_semitones_max:
        violations.append(f"Melodic range {mel_range} exceeds {tier_config.range_semitones_max}.")

    # 3. Start/end scale degree
    start_deg = _scale_degree(melody.key_tonic, melody.key_mode, pitches[0])
    end_deg = _scale_degree(melody.key_tonic, melody.key_mode, pitches[-1])
    if start_deg not in tier_config.start_scale_degrees:
        violations.append(f"Start degree {start_deg} not allowed.")
    if end_deg not in tier_config.end_scale_degrees:
        violations.append(f"End degree {end_deg} not allowed.")

    # 4. Interval rules + stepwise ratio + consecutive leaps
    intervals = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
    abs_intervals = [abs(x) for x in intervals]

    for a in abs_intervals:
        if a in tier_config.forbidden_intervals:
            violations.append(f"Forbidden interval: {a} semitones.")
        if tier_config.allowed_intervals_semitones and a not in tier_config.allowed_intervals_semitones:
            violations.append(f"Interval not allowed: {a} semitones.")

    stepwise = sum(1 for a in abs_intervals if a in (1, 2))
    if abs_intervals:
        stepwise_ratio = stepwise / len(abs_intervals)
        if stepwise_ratio < tier_config.stepwise_ratio_min:
            violations.append(f"Stepwise ratio {stepwise_ratio:.2f} below {tier_config.stepwise_ratio_min:.2f}.")

    # A "leap" is anything > M2 (2 semitones)
    consecutive_leaps = 0
    for a in abs_intervals:
        if a > 2:
            consecutive_leaps += 1
            if consecutive_leaps > tier_config.max_consecutive_leaps:
                violations.append("Too many consecutive leaps.")
                break
        else:
            consecutive_leaps = 0

    passed = len(violations) == 0
    return passed, violations

