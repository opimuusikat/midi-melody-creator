"""
Generate a batch of melodies.

Usage:
  python scripts/generate_batch.py --config config/batch_config.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# Allow running as `python scripts/generate_batch.py` without installing package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_tier_config
from src.diversity_checker import DiversityChecker
from src.melody_generator import generate_one_melody
from src.metadata_extractor import build_metadata
from src.midi_exporter import export_midi
from src.template_library import get_templates_for_tier


def _load_batch_config(path: str | Path) -> dict:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("batch_config must be a mapping")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to batch YAML config")
    args = ap.parse_args()

    cfg = _load_batch_config(args.config)
    batch_id = cfg["batch_id"]
    master_seed = int(cfg["master_seed"])
    total = int(cfg["total_melodies"])
    out_dir = Path(cfg["output_directory"])

    qc = cfg.get("quality_controls", {})
    max_attempts = int(qc.get("max_generation_attempts", 20))
    max_sim = float(qc.get("max_similarity_threshold", 0.20))

    out_dir.mkdir(parents=True, exist_ok=True)

    tier_dist = cfg["tier_distribution"]
    tier_targets = {
        1: int(tier_dist.get("tier1", 0)),
        2: int(tier_dist.get("tier2", 0)),
        3: int(tier_dist.get("tier3", 0)),
    }

    # Load tier configs (tier2/tier3 files may be added later; for smoke test we
    # can re-use tier1 if missing).
    tier_cfg_paths = {
        1: Path("config/tier1.yaml"),
        2: Path("config/tier2.yaml"),
        3: Path("config/tier3.yaml"),
    }

    tier_cfgs = {}
    for t in (1, 2, 3):
        if tier_cfg_paths[t].exists():
            tier_cfgs[t] = load_tier_config(tier_cfg_paths[t])
        else:
            tier_cfgs[t] = load_tier_config(tier_cfg_paths[1])

    dc = DiversityChecker(max_similarity_threshold=max_sim)

    sequence_num = 1
    accepted = 0
    per_tier_accepted = {1: 0, 2: 0, 3: 0}
    attempted = {1: 0, 2: 0, 3: 0}

    for tier in (1, 2, 3):
        templates = get_templates_for_tier(tier)
        tier_cfg = tier_cfgs[tier]
        for _ in range(tier_targets[tier]):
            attempted[tier] += 1
            template = templates[sequence_num % len(templates)]
            melody = generate_one_melody(
                tier_cfg,
                template,
                batch_seed=master_seed,
                sequence_num=sequence_num,
                diversity_checker=dc,
                rng=None,
                max_attempts=max_attempts,
            )
            sequence_num += 1
            if melody is None:
                continue

            midi_path = out_dir / f"{melody.melody_id}.mid"
            json_path = out_dir / f"{melody.melody_id}.json"

            export_midi(melody, midi_path, tempo_bpm=90)
            md = build_metadata(melody, version="1.0.0")
            json_path.write_text(json.dumps(md, indent=2, ensure_ascii=False), encoding="utf-8")

            accepted += 1
            per_tier_accepted[tier] += 1

    manifest = {
        "batch_id": batch_id,
        "master_seed": master_seed,
        "requested_total": total,
        "accepted_total": accepted,
        "accepted_by_tier": per_tier_accepted,
        "attempted_by_tier": attempted,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

