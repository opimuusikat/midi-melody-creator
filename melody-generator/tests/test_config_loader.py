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


def test_load_tier3_all_keys_with_modes_expands(tmp_path: Path):
    yaml_text = """
name: "Advanced"
code: "T3"
keys: "all"
include_modes: true
bar_counts: [1, 2, 3, 4]
meters: ["4/4", "3/4", "2/4"]
durations_normal: ["whole", "half", "quarter", "eighth"]
durations_6_8: []
range_semitones_max: 19
allowed_scale_degrees: [1,2,3,4,5,6,7]
chromatic_allowed: true
chromatic_ratio_max: 0.30
modal_mixture_allowed: true
allowed_intervals_semitones: [1,2,3,4,5,6,7,8,9,10,11,12]
forbidden_intervals: []
max_consecutive_leaps: 3
leap_compensation_required: false
stepwise_ratio_min: 0.40
start_scale_degrees: [1,2,3,4,5,6,7]
end_scale_degrees: [1,2,3,4,5,6,7]
cadence_types: ["authentic", "half", "deceptive", "plagal", "open"]
contour_types: ["arch", "inverted-arch", "ascending", "descending", "wave", "plateau"]
leading_tone_resolution_required: false
prefer_chord_tones_on_strong_beats: false
arch_contour_preference: 0.0
syncopation_allowed: true
tritone_must_resolve_by_step: true
"""
    p = tmp_path / "tier3.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_tier_config(p)
    # 12 tonics × (major+minor) + 12 tonics × 4 modes = 24 + 48 = 72
    assert len(cfg.keys) == 72
    assert {"tonic": "Db", "mode": "major"} in cfg.keys
    assert {"tonic": "Gb", "mode": "mixolydian"} in cfg.keys

