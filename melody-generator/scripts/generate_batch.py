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
    if sum(tier_targets.values()) != total:
        raise ValueError(
            f"total_melodies ({total}) must equal sum(tier_distribution) ({sum(tier_targets.values())})."
        )

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

    dedupe_state_path = out_dir / "dedupe_state.json"
    dc_by_tier: dict[int, DiversityChecker]
    if dedupe_state_path.exists():
        raw = json.loads(dedupe_state_path.read_text(encoding="utf-8"))
        tiers_raw = raw.get("tiers", {}) if isinstance(raw, dict) else {}
        dc_by_tier = {}
        for tier in (1, 2, 3):
            tier_state = tiers_raw.get(str(tier), {}) if isinstance(tiers_raw, dict) else {}
            if isinstance(tier_state, dict):
                dc_by_tier[tier] = DiversityChecker.from_dict(tier_state)
            else:
                dc_by_tier[tier] = DiversityChecker(max_similarity_threshold=max_sim)
            dc_by_tier[tier].max_similarity_threshold = max_sim
    else:
        # Keep deduplication within each tier to avoid starving later tiers in a batch.
        dc_by_tier = {
            1: DiversityChecker(max_similarity_threshold=max_sim),
            2: DiversityChecker(max_similarity_threshold=max_sim),
            3: DiversityChecker(max_similarity_threshold=max_sim),
        }

    sequence_num = 1
    accepted = 0
    per_tier_accepted = {1: 0, 2: 0, 3: 0}
    attempted = {1: 0, 2: 0, 3: 0}

    ensure_key_coverage = bool(cfg.get("ensure_key_coverage", False))

    for tier in (1, 2, 3):
        templates = get_templates_for_tier(tier)
        tier_cfg = tier_cfgs[tier]
        target = tier_targets[tier]

        if ensure_key_coverage and target < len(tier_cfg.keys):
            raise ValueError(
                f"Tier {tier} target ({target}) must be >= number of keys ({len(tier_cfg.keys)}) "
                "when ensure_key_coverage is true."
            )

        # Keep trying until we hit target or exceed a generous attempt budget.
        attempt_budget = target * max_attempts
        if ensure_key_coverage:
            # Key coverage is stricter: allow more retries, especially for T3.
            attempt_budget *= 10

        # If requested, force at least one melody per key for each tier.
        forced_key_queue: list[dict] = []
        if ensure_key_coverage:
            forced_key_queue = list(tier_cfg.keys)

        while per_tier_accepted[tier] < target and attempted[tier] < attempt_budget:
            attempted[tier] += 1
            template = templates[sequence_num % len(templates)]
            # Important: only advance the forced-key queue on *success*.
            forced_key = forced_key_queue[0] if forced_key_queue else None
            melody = generate_one_melody(
                tier_cfg,
                template,
                batch_seed=master_seed,
                sequence_num=sequence_num,
                diversity_checker=dc_by_tier[tier],
                rng=None,
                max_attempts=max_attempts,
                forced_key=forced_key,
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
            if forced_key_queue:
                forced_key_queue.pop(0)
            if per_tier_accepted[tier] % 50 == 0:
                print(
                    f"tier {tier}: accepted {per_tier_accepted[tier]}/{target} (attempted {attempted[tier]})",
                    flush=True,
                )

        if per_tier_accepted[tier] != target:
            raise RuntimeError(
                f"Failed to reach tier {tier} target: accepted {per_tier_accepted[tier]} / {target} "
                f"after {attempted[tier]} attempts."
            )

    manifest = {
        "batch_id": batch_id,
        "master_seed": master_seed,
        "requested_total": total,
        "accepted_total": accepted,
        "accepted_by_tier": per_tier_accepted,
        "attempted_by_tier": attempted,
        "ensure_key_coverage": ensure_key_coverage,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    dedupe_state = {"version": 1, "tiers": {str(t): dc_by_tier[t].to_dict() for t in (1, 2, 3)}}
    dedupe_state_path.write_text(json.dumps(dedupe_state, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

