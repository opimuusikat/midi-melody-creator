from __future__ import annotations

"""
Helpers for interacting with music21.

music21 uses a particular spelling for flats (e.g. "B-" for Bb). Our configs use
more common "Bb"/"Db" strings. These helpers provide consistent conversion and
mode-aware scale creation so generation works across flat keys and modes.
"""

from music21 import key as m21key
from music21 import scale as m21scale


def tonic_to_music21(tonic: str) -> str:
    """
    Convert config tonic spelling to music21 spelling.

    Examples:
    - "Bb" -> "B-"
    - "Db" -> "D-"
    - "Gb" -> "G-"
    - "F#" -> "F#"
    - "C"  -> "C"
    """

    t = tonic.strip()
    if len(t) >= 2 and t.endswith("b"):
        return f"{t[0]}-"
    return t


def make_key_or_scale(tonic: str, mode: str):
    """
    Return a music21 Key or Scale that represents the pitch collection for (tonic, mode).

    For major/minor we use `music21.key.Key`. For church modes we use the
    dedicated Scale classes (these behave more consistently than Key for modes).
    """

    t = tonic_to_music21(tonic)
    m = mode.strip().lower()

    if m in ("major", "minor"):
        return m21key.Key(t, m)

    mode_to_scale = {
        "dorian": m21scale.DorianScale,
        "phrygian": m21scale.PhrygianScale,
        "lydian": m21scale.LydianScale,
        "mixolydian": m21scale.MixolydianScale,
    }
    cls = mode_to_scale.get(m)
    if cls is None:
        # Best-effort fallback; some mode strings may still work with Key.
        return m21key.Key(t, mode)

    return cls(t)

