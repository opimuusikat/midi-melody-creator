from src.metadata_extractor import build_metadata
from src.models import Melody, Note


def test_metadata_contains_required_top_level_fields():
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
        notes=[Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1)],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=42,
        template_id="T1_template",
    )
    md = build_metadata(m, version="1.0.0")
    assert md["id"] == "T1_Cmaj_44_1bar_arch_0001"
    assert "tonal" in md and "melodic" in md and "rhythmic" in md

