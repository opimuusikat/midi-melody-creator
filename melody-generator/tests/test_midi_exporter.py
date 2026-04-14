from pathlib import Path

import pretty_midi

from src.midi_exporter import export_midi
from src.models import Melody, Note


def test_export_midi_writes_readable_file(tmp_path: Path):
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
        ],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    out = tmp_path / "x.mid"
    export_midi(m, out, tempo_bpm=90)
    pm = pretty_midi.PrettyMIDI(str(out))
    assert len(pm.instruments) == 1
    assert len(pm.instruments[0].notes) == 2

