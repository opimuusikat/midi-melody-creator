from __future__ import annotations

"""
Generate simple target contour curves for melodies.

A contour curve is a list of floats in the range [0, 1]. The pitch generator uses
these values as a soft target to bias note choice over time (e.g., an "arch"
contour rises then falls).
"""

from typing import Callable

import numpy as np


def _normalize_to_unit(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def arch_contour(num_notes: int) -> list[float]:
    """Starts low, peaks in the middle, ends low."""
    if num_notes <= 0:
        return []
    vals = np.sin(np.linspace(0.0, np.pi, num_notes)).tolist()
    return _normalize_to_unit([float(v) for v in vals])


def inverted_arch_contour(num_notes: int) -> list[float]:
    """Starts high, dips in the middle, ends high."""
    if num_notes <= 0:
        return []
    vals = (1.0 - np.sin(np.linspace(0.0, np.pi, num_notes))).tolist()
    return _normalize_to_unit([float(v) for v in vals])


def ascending_contour(num_notes: int) -> list[float]:
    if num_notes <= 0:
        return []
    return np.linspace(0.0, 1.0, num_notes).astype(float).tolist()


def descending_contour(num_notes: int) -> list[float]:
    if num_notes <= 0:
        return []
    return np.linspace(1.0, 0.0, num_notes).astype(float).tolist()


def wave_contour(num_notes: int) -> list[float]:
    """A gentle wave with one full up/down cycle."""
    if num_notes <= 0:
        return []
    vals = (np.sin(np.linspace(0.0, 2.0 * np.pi, num_notes)) + 1.0).tolist()
    return _normalize_to_unit([float(v) for v in vals])


def plateau_contour(num_notes: int) -> list[float]:
    """Mostly flat, with a small middle bump."""
    if num_notes <= 0:
        return []
    if num_notes <= 2:
        return [0.5 for _ in range(num_notes)]
    vals = [0.4] * num_notes
    mid = num_notes // 2
    vals[mid] = 0.6
    if num_notes > 4:
        vals[mid - 1] = 0.55
        vals[mid + 1] = 0.55
    return _normalize_to_unit(vals)


_CONTOURS: dict[str, Callable[[int], list[float]]] = {
    "arch": arch_contour,
    "ascending": ascending_contour,
    "descending": descending_contour,
    "wave": wave_contour,
    "inverted-arch": inverted_arch_contour,
    "plateau": plateau_contour,
}


def get_contour_curve(contour_type: str, num_notes: int) -> list[float]:
    fn = _CONTOURS.get(contour_type)
    if fn is None:
        raise ValueError(f"Unknown contour type '{contour_type}'")
    curve = fn(num_notes)
    # Defensive clamp in case of float edge cases
    return [min(1.0, max(0.0, float(x))) for x in curve]

