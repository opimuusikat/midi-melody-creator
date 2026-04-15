from __future__ import annotations

from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

import yaml

from src.models import TierConfig


def _expand_all_keys(*, include_modes: bool) -> list[dict[str, str]]:
    tonics = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    keys: list[dict[str, str]] = []

    for tonic in tonics:
        keys.append({"tonic": tonic, "mode": "major"})
        keys.append({"tonic": tonic, "mode": "minor"})

    if include_modes:
        # Keep in sync with website-facing dictation rulebook (v1): tier 2 adds
        # dorian/mixolydian and tier 3 adds phrygian/lydian.
        modes = ["dorian", "phrygian", "lydian", "mixolydian"]
        for tonic in tonics:
            for mode in modes:
                keys.append({"tonic": tonic, "mode": mode})

    return keys


def load_tier_config(path: str | Path) -> TierConfig:
    """
    Load a tier YAML file into a TierConfig dataclass.

    This loader is intentionally strict about required fields (those defined in
    TierConfig without defaults) and permissive about field ordering.
    """

    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Tier config must be a mapping, got: {type(data).__name__}")

    # Support shorthand: keys: "all" (+ include_modes flag).
    if data.get("keys") == "all":
        include_modes = bool(data.get("include_modes", False))
        data = dict(data)
        data["keys"] = _expand_all_keys(include_modes=include_modes)

    tier_fields = {f.name: f for f in fields(TierConfig)}
    kwargs: dict[str, Any] = {}

    for name, f in tier_fields.items():
        if name in data:
            kwargs[name] = data[name]
            continue

        # If missing: require it unless the dataclass provides a default.
        has_default = f.default is not MISSING
        has_default_factory = getattr(f, "default_factory", MISSING) is not MISSING  # type: ignore[attr-defined]
        if has_default or has_default_factory:
            continue

        raise ValueError(f"Missing required tier field '{name}' in {p}")

    return TierConfig(**kwargs)

