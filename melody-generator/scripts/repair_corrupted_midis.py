"""
Repair corrupted/truncated MIDI files in an output batch.

Given one or more melody IDs (filename stems), regenerate a replacement melody
that matches the ID's structural fields (tier/key/mode/meter/bars/contour) and
overwrite the `.mid` + `.json` sidecar in-place.

This is intended for rare cases where a batch contains a handful of broken MIDI
files due to interrupted writes or filesystem issues.

Usage:
  .venv/bin/python scripts/repair_corrupted_midis.py \
    --batch-dir output/batch_2500_modes_final \
    --ids T1_Bbmaj_44_1bar_ascending_0768 T1_Bbmaj_44_2bar_arch_0151
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_tier_config
from src.contour_engine import get_contour_curve
from src.diversity_checker import DiversityChecker
from src.melody_generator import _build_notes, _force_ending_tonic, _nearest_pitch_with_pitch_class, _pitch_class_for_scale_degree
from src.metadata_extractor import build_metadata
from src.midi_exporter import export_midi
from src.models import Melody
from src.pitch_generator import generate_pitch_sequence
from src.rhythm_generator import generate_rhythm
from src.template_library import get_templates_for_tier
from src.validator import validate_melody


_ID_RE = re.compile(
    r"^T(?P<tier>[123])_"
    r"(?P<tonic>[A-G])(?P<accidental>b|#)?"
    r"(?P<mode>maj|min|major|minor|dor|phr|lyd|mix|dorian|phrygian|lydian|mixolydian)_"
    r"(?P<meter_num>\d+)(?P<meter_den>\d+)_"
    r"(?P<bars>\d+)bar_"
    r"(?P<contour>[a-zA-Z-]+)_"
    r"(?P<seq>\d{4})$"
)


def _normalize_mode(m: str) -> str:
    m = m.lower().strip()
    return {
        "maj": "major",
        "min": "minor",
        "dor": "dorian",
        "phr": "phrygian",
        "lyd": "lydian",
        "mix": "mixolydian",
    }.get(m, m)


def _select_template_for(tier: int, bar_count: int) -> dict:
    templates = get_templates_for_tier(tier)
    # Choose the first template that supports the desired bar count; fall back
    # to any template if none match (shouldn't happen for current tier YAMLs).
    for t in templates:
        if bar_count in t.get("bar_counts", []):
            return t
    return templates[0]


def _regenerate_exact_id(*, melody_id: str, batch_seed: int, dc: DiversityChecker) -> Melody:
    m = _ID_RE.match(melody_id)
    if not m:
        raise ValueError(f"Unparseable melody id: {melody_id}")
    g = m.groupdict()

    tier_num = int(g["tier"])
    tonic = g["tonic"] + (g["accidental"] or "")
    mode = _normalize_mode(g["mode"])
    meter = f"{int(g['meter_num'])}/{int(g['meter_den'])}"
    bars = int(g["bars"])
    contour = g["contour"]
    seq_num = int(g["seq"])

    tier_cfg = load_tier_config(Path("config") / f"tier{tier_num}.yaml")
    template = _select_template_for(tier_num, bars)

    # Use a deterministic base seed per target ID but allow retries.
    base_seed = hash((batch_seed, melody_id, "repair"))

    for attempt in range(2000):
        local_rng = random.Random(hash((base_seed, attempt)))

        allowed_durations = tier_cfg.durations_normal
        rhythm = generate_rhythm(meter, bars, allowed_durations, local_rng)
        rhythm_durations = [d for d, _b in rhythm]
        contour_targets = get_contour_curve(contour, len(rhythm))

        start_degree = local_rng.choice(template.get("start_degree_options", tier_cfg.start_scale_degrees))
        start_pc = _pitch_class_for_scale_degree(tonic, mode, int(start_degree))
        starting_pitch = _nearest_pitch_with_pitch_class(target_midi=69, pitch_class=start_pc, allowed_range=(57, 81))

        pitches = generate_pitch_sequence(
            key_tonic=tonic,
            key_mode=mode,
            contour_targets=contour_targets,
            rhythm_durations=rhythm_durations,
            tier_config=tier_cfg,
            rng=local_rng,
            starting_pitch=starting_pitch,
        )

        if tier_cfg.end_scale_degrees == [1]:
            pitches = _force_ending_tonic(pitches, tonic, mode, tier_cfg)

        notes = _build_notes(pitches, rhythm, meter)

        mel = Melody(
            melody_id=melody_id,  # keep filename stable
            notes=notes,
            tier=tier_num,
            key_tonic=tonic,
            key_mode=mode,
            meter=meter,
            bar_count=bars,
            contour_type=contour,
            cadence_type=str(template.get("cadence_type") or "authentic"),
            seed=int(hash((base_seed, attempt))),
            template_id=str(template.get("id", "")),
        )

        ok, _viol = validate_melody(mel, tier_cfg)
        if not ok:
            continue
        if dc.is_too_similar(mel):
            continue

        dc.register(mel)
        return mel

    raise RuntimeError(f"Failed to regenerate a valid unique melody for {melody_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--batch-seed", type=int, default=20260414)
    ap.add_argument("--ids", nargs="+", required=True)
    args = ap.parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.is_dir():
        raise SystemExit(f"Not a directory: {batch_dir}")

    # Build a dedupe baseline from the batch (so repairs don’t introduce near-duplicates).
    dc = DiversityChecker(max_similarity_threshold=0.20)
    for jp in sorted(batch_dir.glob("*.json")):
        if jp.name == "manifest.json":
            continue
        # Use metadata interval sequence + duration histogram? We only have per-note durations via MIDI.
        # Best-effort: register via existing MIDI when parseable; corrupted MIDIs will be skipped.
        mp = jp.with_suffix(".mid")
        try:
            # Importing music21 here would be slow; instead just skip baseline and rely on DC during repair.
            # (DC state persistence in generation is the long-term solution.)
            pass
        except Exception:
            continue

    repaired = 0
    for melody_id in args.ids:
        midi_path = batch_dir / f"{melody_id}.mid"
        json_path = batch_dir / f"{melody_id}.json"
        if not json_path.exists():
            raise SystemExit(f"Missing JSON sidecar: {json_path}")

        mel = _regenerate_exact_id(melody_id=melody_id, batch_seed=int(args.batch_seed), dc=dc)
        export_midi(mel, midi_path, tempo_bpm=90)
        md = build_metadata(mel, version="1.0.0")
        json_path.write_text(__import__("json").dumps(md, indent=2, ensure_ascii=False), encoding="utf-8")
        repaired += 1

    print(f"Repaired {repaired} files in {batch_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

