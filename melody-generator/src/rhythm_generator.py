from __future__ import annotations

"""
Rhythm generation for monophonic melodies.

Given a meter (4/4, 3/4, 2/4), a number of bars, and an allowed duration set,
this module returns a rhythm that exactly fills the requested time with no rests.
"""

from typing import Iterable


DURATION_BEATS: dict[str, float] = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
}

METER_BEATS_PER_BAR: dict[str, float] = {
    "4/4": 4.0,
    "3/4": 3.0,
    "2/4": 2.0,
}


def _allowed_beats(allowed_durations: Iterable[str]) -> list[float]:
    beats: list[float] = []
    for name in allowed_durations:
        if name not in DURATION_BEATS:
            raise ValueError(f"Unknown duration '{name}'")
        beats.append(DURATION_BEATS[name])
    # Prefer larger values first to reduce recursion branching.
    return sorted(beats, reverse=True)


def generate_rhythm(
    meter: str, bar_count: int, allowed_durations: list[str], rng
) -> list[tuple[str, float]]:
    """
    Returns a rhythm as a list of (duration_name, duration_beats) tuples that
    exactly fills `bar_count` bars of `meter`.
    """

    if meter not in METER_BEATS_PER_BAR:
        raise ValueError(f"Unsupported meter '{meter}' (v1 supports 4/4, 3/4, 2/4)")
    if bar_count <= 0:
        raise ValueError("bar_count must be positive")
    if not allowed_durations:
        raise ValueError("allowed_durations must be non-empty")

    allowed = _allowed_beats(allowed_durations)

    # Dictation v1 export rulebook requires that a note must not cross a bar
    # boundary. To guarantee this, fill each bar independently.
    bar_beats = METER_BEATS_PER_BAR[meter]

    out: list[tuple[str, float]] = []
    for _bar_idx in range(bar_count):
        remaining = bar_beats
        bar_out: list[tuple[str, float]] = []

        # Protect against infinite loops from floating point issues.
        for _ in range(10_000):
            if abs(remaining) < 1e-9:
                break

            fitting = [b for b in allowed if b <= remaining + 1e-9]
            if not fitting:
                # If we got stuck due to earlier random choices, restart this bar.
                remaining = bar_beats
                bar_out = []
                continue

            # Weighted choice: larger durations are slightly more likely.
            weights = [(b * b) for b in fitting]
            choice = rng.choices(fitting, weights=weights, k=1)[0]

            # Find name for chosen beat length (stable mapping).
            name = next(k for k, v in DURATION_BEATS.items() if v == choice)
            bar_out.append((name, choice))
            remaining -= choice

        if abs(remaining) >= 1e-6:
            raise RuntimeError("Failed to generate rhythm that exactly fills one bar")

        out.extend(bar_out)

    return out

