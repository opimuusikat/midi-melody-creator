from __future__ import annotations

from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

import yaml

from src.models import TierConfig


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

