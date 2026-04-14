"""
Finalize a generated batch into a "final" directory.

Copies:
  - *.mid
  - for each MIDI stem, a matching .json sidecar (required)
  - manifest.json (required)

Optionally validates expected tier counts based on MIDI filename prefixes:
  - T1_, T2_, T3_

Usage:
  python scripts/finalize_batch.py --source-dir output/batch_x --final-dir output/batch_x_final
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _count_tiers(source_dir: Path) -> dict[int, int]:
    counts = {1: 0, 2: 0, 3: 0}
    for p in source_dir.glob("*.mid"):
        stem = p.stem
        if stem.startswith("T1_"):
            counts[1] += 1
        elif stem.startswith("T2_"):
            counts[2] += 1
        elif stem.startswith("T3_"):
            counts[3] += 1
    return counts


def _dir_has_any_files(p: Path) -> bool:
    if not p.exists() or not p.is_dir():
        return False
    return any(p.iterdir())


def _safe_rmtree(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


def _safe_rmdir_if_empty(p: Path) -> None:
    if p.exists() and p.is_dir() and not any(p.iterdir()):
        p.rmdir()


def _copy_finalized_outputs(source_dir: Path, tmp_dir: Path) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)

    manifest_src = source_dir / "manifest.json"
    shutil.copy2(manifest_src, tmp_dir / "manifest.json")

    midi_paths = sorted(source_dir.glob("*.mid"))
    for midi_src in midi_paths:
        shutil.copy2(midi_src, tmp_dir / midi_src.name)

        sidecar_src = source_dir / f"{midi_src.stem}.json"
        if not sidecar_src.exists():
            raise FileNotFoundError(
                f"Missing required sidecar JSON for MIDI: {midi_src.name} "
                f"(expected {sidecar_src.name})"
            )
        shutil.copy2(sidecar_src, tmp_dir / sidecar_src.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, help="Directory containing batch outputs")
    ap.add_argument("--final-dir", required=True, help="Directory to copy finalized outputs into")
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing non-empty final dir",
    )
    ap.add_argument("--expected-tier1", type=int, default=None)
    ap.add_argument("--expected-tier2", type=int, default=None)
    ap.add_argument("--expected-tier3", type=int, default=None)
    args = ap.parse_args()

    source_dir = Path(args.source_dir)
    final_dir = Path(args.final_dir)
    tmp_dir = final_dir.parent / f"{final_dir.name}._tmp_finalize"

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Not a directory: {source_dir}", file=sys.stderr)
        return 2

    manifest_src = source_dir / "manifest.json"
    if not manifest_src.exists():
        print(f"Missing manifest.json in source dir: {source_dir}", file=sys.stderr)
        return 2

    if _dir_has_any_files(final_dir) and not args.overwrite:
        print(
            f"Final dir exists and is not empty: {final_dir}. "
            f"Use --overwrite to replace it.",
            file=sys.stderr,
        )
        return 2

    if tmp_dir.exists():
        if args.overwrite:
            _safe_rmtree(tmp_dir)
        else:
            print(
                f"Temp finalize dir already exists: {tmp_dir}. "
                f"Remove it or re-run with --overwrite.",
                file=sys.stderr,
            )
            return 2

    counts = _count_tiers(source_dir)
    expected = {1: args.expected_tier1, 2: args.expected_tier2, 3: args.expected_tier3}
    mismatches: list[str] = []
    for tier in (1, 2, 3):
        exp = expected[tier]
        if exp is None:
            continue
        got = counts[tier]
        if got != exp:
            mismatches.append(f"tier{tier}: expected {exp}, got {got}")

    if mismatches:
        print(
            "Tier count mismatch. "
            f"got_counts={counts} expected_counts={expected}. "
            + "; ".join(mismatches),
            file=sys.stderr,
        )
        return 3

    try:
        _copy_finalized_outputs(source_dir, tmp_dir)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        _safe_rmtree(tmp_dir)
        return 3
    except Exception as e:
        print(f"Finalize failed while copying: {e}", file=sys.stderr)
        _safe_rmtree(tmp_dir)
        return 2

    if args.overwrite:
        _safe_rmtree(final_dir)
    else:
        # If final_dir exists but is empty, remove it so the atomic rename can succeed.
        _safe_rmdir_if_empty(final_dir)
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.rename(final_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

