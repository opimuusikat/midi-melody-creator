from __future__ import annotations

"""
Helpers for interacting with music21.

music21 uses a particular spelling for flats (e.g. "B-" for Bb). Our configs use
more common "Bb"/"Db" strings. These helpers provide consistent conversion so
generation/validation works across flat keys.
"""


def tonic_to_music21(tonic: str) -> str:
    """
    Convert config tonic spelling to music21 spelling.

    Examples:
    - "Bb" -> "B-"
    - "Db" -> "D-"
    - "F#" -> "F#"
    - "C"  -> "C"
    """

    t = tonic.strip()
    if len(t) >= 2 and t.endswith("b"):
        return f"{t[0]}-"
    return t

