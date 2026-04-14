from __future__ import annotations

"""
Difficulty scoring for generated melodies.

Implements the composite score described in the original spec:

D = 3.0·I + 2.5·C + 2.0·L + 1.5·R + 1.5·V + 1.0·P + 2.0·T
"""

from collections import Counter

from src.models import Melody


_INTERVAL_WEIGHTS: dict[int, float] = {
    0: 0.0,
    1: 0.5,
    2: 0.5,
    3: 1.0,
    4: 1.0,
    5: 1.5,
    6: 3.0,
    7: 1.5,
    8: 2.5,  # m6
    9: 2.0,  # M6
    10: 3.0,  # m7
    11: 3.5,  # M7
    12: 2.0,  # P8
}


def score_melody(melody: Melody) -> tuple[float, dict[str, float]]:
    notes = melody.notes
    pitches = [n.midi_pitch for n in notes]
    durations = [n.duration for n in notes]

    intervals = [abs(pitches[i + 1] - pitches[i]) for i in range(len(pitches) - 1)]
    if intervals:
        I = sum(_INTERVAL_WEIGHTS.get(i, 3.5) for i in intervals) / len(intervals)
    else:
        I = 0.0

    # Chromatic ratio unknown at this layer in v1 (generation is mostly diatonic);
    # keep as 0.0 and let metadata layer compute if needed later.
    C = 0.0

    L = 0.0
    if intervals:
        L = sum(1 for i in intervals if i > 2) / len(intervals)

    pitch_range = max(pitches) - min(pitches) if pitches else 0
    R = pitch_range / 24.0

    unique_durations = len(set(durations)) if durations else 0
    V = (unique_durations / len(durations)) if durations else 0.0

    P = min((len(notes) / 16.0) if notes else 0.0, 1.0)

    # Tonal instability (T): proxy based on scale-degree chord-tone ratio is
    # computed later with key context. For now keep as 0.0.
    T = 0.0

    composite = 3.0 * I + 2.5 * C + 2.0 * L + 1.5 * R + 1.5 * V + 1.0 * P + 2.0 * T
    subs = {
        "interval_difficulty": float(I),
        "chromatic_content": float(C),
        "leap_frequency": float(L),
        "range_normalized": float(R),
        "rhythmic_variety": float(V),
        "phrase_length": float(P),
        "tonal_instability": float(T),
    }
    return float(composite), subs

