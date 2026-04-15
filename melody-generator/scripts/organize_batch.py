"""
Organize a flat batch output folder into a browsable structure.

Input batch folders currently look like:
  output/<batch_id>/
    <melody_id>.mid
    <melody_id>.json
    manifest.json

This script reorganizes into:
  <out>/<batch_id>/
    manifest.json
    dedupe_state.json  (if present in input)
    tier1/major|minor|modal/
    tier2/major|minor|modal/
    tier3/major|minor|modal/

Files are copied by default (so original batch stays intact).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _bucket_for_mode(mode: str) -> str:
    m = (mode or "").strip().lower()
    if m == "major":
        return "major"
    if m == "minor":
        return "minor"
    return "modal"


def _tier_dir_name(tier: int) -> str:
    return {1: "tier1", 2: "tier2", 3: "tier3"}.get(int(tier), f"tier{tier}")


def organize_batch(*, input_dir: Path, output_dir: Path, move: bool) -> None:
    if not input_dir.exists():
        raise FileNotFoundError(str(input_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_src = input_dir / "manifest.json"
    if manifest_src.exists():
        shutil.copy2(manifest_src, output_dir / "manifest.json")

    dedupe_src = input_dir / "dedupe_state.json"
    if dedupe_src.exists():
        shutil.copy2(dedupe_src, output_dir / "dedupe_state.json")

    skip_json = {"manifest.json", "dedupe_state.json"}
    json_files = [p for p in input_dir.glob("*.json") if p.name not in skip_json]
    for jp in json_files:
        data = json.loads(jp.read_text(encoding="utf-8"))
        tier = int(data["difficulty"]["tier"])
        mode = data["tonal"]["mode"]
        bucket = _bucket_for_mode(mode)

        dest_dir = output_dir / _tier_dir_name(tier) / bucket
        dest_dir.mkdir(parents=True, exist_ok=True)

        midi_name = data["file"]["midi_filename"]
        midi_src = input_dir / midi_name
        midi_dest = dest_dir / midi_name
        json_dest = dest_dir / jp.name

        if move:
            shutil.move(str(midi_src), str(midi_dest))
            shutil.move(str(jp), str(json_dest))
        else:
            shutil.copy2(midi_src, midi_dest)
            shutil.copy2(jp, json_dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Flat batch folder (contains .mid/.json/manifest.json)")
    ap.add_argument("--output", required=True, help="Destination folder for organized output")
    ap.add_argument("--move", action="store_true", help="Move files instead of copying (destructive)")
    args = ap.parse_args()

    organize_batch(input_dir=Path(args.input), output_dir=Path(args.output), move=bool(args.move))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

