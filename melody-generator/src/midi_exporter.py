from __future__ import annotations

"""
MIDI file export.

Uses pretty_midi for simple, reliable MIDI writing.
"""

from pathlib import Path

import pretty_midi

from src.models import Melody
from src.rhythm_generator import DURATION_BEATS


def export_midi(melody: Melody, filepath: str | Path, *, tempo_bpm: int = 90) -> None:
    # Use a PPQ that represents 1/8 notes cleanly to avoid downstream parsers
    # reconstructing non-whitelisted durations from tick rounding.
    pm = pretty_midi.PrettyMIDI(resolution=480, initial_tempo=float(tempo_bpm))
    inst = pretty_midi.Instrument(program=0)  # Acoustic Grand Piano

    # Encode meter explicitly so "bar boundary" is well-defined for consumers.
    try:
        num_s, den_s = str(melody.meter).split("/")
        pm.time_signature_changes = [
            pretty_midi.TimeSignature(int(num_s), int(den_s), 0.0),
        ]
    except Exception:
        # Best-effort: if meter is malformed, still export monophonic timing.
        pass

    seconds_per_beat = 60.0 / float(tempo_bpm)
    current_time = 0.0

    for n in melody.notes:
        dur_beats = DURATION_BEATS[n.duration]
        dur_seconds = dur_beats * seconds_per_beat
        pm_note = pretty_midi.Note(
            velocity=80,
            pitch=int(n.midi_pitch),
            start=float(current_time),
            end=float(current_time + dur_seconds),
        )
        inst.notes.append(pm_note)
        current_time += dur_seconds

    pm.instruments.append(inst)
    pm.write(str(filepath))

