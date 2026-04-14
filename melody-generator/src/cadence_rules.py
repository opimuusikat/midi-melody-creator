from __future__ import annotations

"""
Cadence scale-degree sequences.

Cadences are expressed as scale degrees (1..7) rather than absolute pitches.
These sequences are used as targets for the final notes of a phrase.
"""

from typing import Optional

import random


CADENCE_TEMPLATES: dict[str, list[Optional[list[int]]]] = {
    "authentic": [
        [2, 1],
        [7, 1],
        [4, 3, 2, 1],
        [5, 1],
    ],
    "half": [
        [1, 2],
        [3, 2],
        [1, 7],
        [4, 5],
    ],
    "deceptive": [
        [2, 3],
        [7, 1],
    ],
    "plagal": [
        [4, 3],
        [6, 5],
        [1, 1],
    ],
    "open": [
        None,
    ],
}


def get_cadence_degrees(
    cadence_type: str, *, rng_seed: int | None = None, rng: random.Random | None = None
) -> Optional[list[int]]:
    if cadence_type not in CADENCE_TEMPLATES:
        raise ValueError(f"Unknown cadence type '{cadence_type}'")

    if rng is None:
        rng = random.Random(rng_seed)

    return rng.choice(CADENCE_TEMPLATES[cadence_type])

