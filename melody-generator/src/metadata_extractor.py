from __future__ import annotations

"""
Build per-melody metadata JSON.

The website will query this JSON to filter/search exercise material, so the
schema must remain stable.
"""

from collections import Counter
from datetime import datetime, timezone

from music21 import pitch as m21pitch

from src.difficulty_scorer import score_melody
from src.models import Melody


_MODE_ABBREV: dict[str, str] = {
    "major": "maj",
    "minor": "min",
    "dorian": "dor",
    "phrygian": "phr",
    "lydian": "lyd",
    "mixolydian": "mix",
}


def _pitch_name(midi: int) -> str:
    p = m21pitch.Pitch()
    p.midi = midi
    return p.nameWithOctave


def build_metadata(melody: Melody, *, version: str) -> dict:
    pitches = [n.midi_pitch for n in melody.notes]
    durations = [n.duration for n in melody.notes]
    intervals = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]

    chromatic_note_count = 0
    chromatic_ratio = 0.0

    composite, subs = score_melody(melody)

    md = {
        "id": melody.melody_id,
        "version": version,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "seed": melody.seed,
        "tonal": {
            "key": melody.key_tonic,
            "mode": melody.key_mode,
            "scale_type": "diatonic",
            "chromatic_note_count": chromatic_note_count,
            "chromatic_ratio": chromatic_ratio,
        },
        "melodic": {
            "num_notes": len(melody.notes),
            "pitch_lowest": _pitch_name(min(pitches)),
            "pitch_highest": _pitch_name(max(pitches)),
            "pitch_lowest_midi": int(min(pitches)),
            "pitch_highest_midi": int(max(pitches)),
            "range_semitones": int(max(pitches) - min(pitches)),
            "interval_histogram": dict(Counter(intervals)),
            "largest_leap_semitones": int(max((abs(i) for i in intervals), default=0)),
            "stepwise_ratio": float(
                (sum(1 for i in intervals if abs(i) in (1, 2)) / len(intervals)) if intervals else 1.0
            ),
            "leap_ratio": float((sum(1 for i in intervals if abs(i) > 2) / len(intervals)) if intervals else 0.0),
            "contour_type": melody.contour_type,
            "contour_parsons": "".join("U" if i > 0 else "D" if i < 0 else "R" for i in intervals),
            "starting_degree": None,  # filled later once we standardize degree calc
            "ending_degree": None,
        },
        "rhythmic": {
            "meter": melody.meter,
            "bar_count": melody.bar_count,
            "total_beats": None,  # filled later when rhythm module exposes beat-sums in notes
            "note_count": len(melody.notes),
            "duration_histogram": dict(Counter(durations)),
            "suggested_tempo_bpm": 90,
        },
        "cadence": {
            "type": melody.cadence_type,
            "final_degrees": None,
        },
        "difficulty": {
            "tier": melody.tier,
            "composite_score": float(composite),
            "sub_scores": subs,
        },
        "file": {
            "midi_filename": f"{melody.melody_id}.mid",
            "interval_sequence": intervals,
        },
    }

    return md

