import random

from src.config_loader import load_tier_config
from src.diversity_checker import DiversityChecker
from src.melody_generator import generate_one_melody
from src.template_library import get_templates_for_tier


def test_generate_one_melody_produces_valid_non_duplicate():
    cfg = load_tier_config("config/tier1.yaml")
    templates = get_templates_for_tier(1)
    rng = random.Random(123)
    dc = DiversityChecker(max_similarity_threshold=0.2)
    # Tier 1 constraints can be strict; allow more retries to avoid flakiness
    # when configs evolve (e.g., stricter cadence approach / density caps).
    m = generate_one_melody(
        cfg, templates[0], batch_seed=20260414, sequence_num=1, diversity_checker=dc, rng=rng, max_attempts=200
    )
    assert m is not None
    assert len(m.notes) > 0
    assert all(57 <= n.midi_pitch <= 81 for n in m.notes)


def test_generate_batch_cli_smoke(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    out_dir: Path = tmp_path / "out"
    cfg_path: Path = tmp_path / "batch.yaml"
    cfg_path.write_text(
        f'''
batch_id: "batch_test"
master_seed: 20260414
total_melodies: 6
tier_distribution:
  tier1: 2
  tier2: 2
  tier3: 2
meter_weights:
  "4/4": 0.50
  "3/4": 0.30
  "2/4": 0.20
output_directory: "{out_dir.as_posix()}"
quality_controls:
  max_generation_attempts: 10
  max_similarity_threshold: 0.20
''',
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "scripts/generate_batch.py", "--config", str(cfg_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    manifest = out_dir / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["batch_id"] == "batch_test"

