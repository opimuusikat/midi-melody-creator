from pathlib import Path

from src.config_loader import load_tier_config


def test_load_tier1_yaml_to_dataclass(tmp_path: Path):
    yaml_text = """
name: "Beginner"
code: "T1"
keys:
  - {tonic: "C", mode: "major"}
bar_counts: [1, 2]
meters: ["4/4", "3/4", "2/4"]
durations_normal: ["quarter", "eighth"]
durations_6_8: []
range_semitones_max: 12
allowed_scale_degrees: [1,2,3,4,5,6,7]
chromatic_allowed: false
chromatic_ratio_max: 0.0
modal_mixture_allowed: false
allowed_intervals_semitones: [1,2,3,4,5,7]
forbidden_intervals: [6,10,11]
max_consecutive_leaps: 1
leap_compensation_required: true
stepwise_ratio_min: 0.70
start_scale_degrees: [1,3,5]
end_scale_degrees: [1]
cadence_types: ["authentic"]
contour_types: ["arch", "ascending", "descending"]
leading_tone_resolution_required: true
prefer_chord_tones_on_strong_beats: true
arch_contour_preference: 0.60
syncopation_allowed: false
tritone_must_resolve_by_step: false
"""
    p = tmp_path / "tier1.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_tier_config(p)
    assert cfg.code == "T1"
    assert "4/4" in cfg.meters
    assert cfg.chromatic_allowed is False

