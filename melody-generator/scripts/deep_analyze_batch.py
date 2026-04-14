"""
Deep analysis for a generated melody batch (Option 3).

Reads the batch's per-melody JSON sidecars (and optionally MIDI for a small set
of cadence/ending heuristics), then writes:
  - _analysis/summary.json
  - _analysis/summary.md
  - _analysis/outliers.csv
  - _analysis/near_duplicates.csv

Usage:
  .venv/bin/python scripts/deep_analyze_batch.py --batch-dir output/batch_2500_modes_final
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Allow running as `python scripts/...` without installing package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from music21 import converter as m21converter  # type: ignore

from src.music21_utils import make_key_or_scale


_FILENAME_RE = re.compile(
    r"^T(?P<tier>[123])_"
    r"(?P<tonic>[A-G])(?P<accidental>b|#)?"
    r"(?P<mode>maj|min|major|minor|dor|phr|lyd|mix|dorian|phrygian|lydian|mixolydian)_"
    r"(?P<meter_num>\d+)(?P<meter_den>\d+)_"
    r"(?P<bars>\d+)bar_"
    r"(?P<contour>[a-zA-Z-]+)_"
    r"(?P<seq>\d{4})$"
)


def _normalize_mode(mode: str) -> str:
    m = mode.lower().strip()
    if m == "maj":
        return "major"
    if m == "min":
        return "minor"
    if m == "dor":
        return "dorian"
    if m == "phr":
        return "phrygian"
    if m == "lyd":
        return "lydian"
    if m == "mix":
        return "mixolydian"
    return m


def _bar_len_quarter(meter_num: int, meter_den: int) -> float:
    return float(meter_num) * (4.0 / float(meter_den))


def _safe_float(x) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    vs = sorted(values)
    if p <= 0:
        return vs[0]
    if p >= 100:
        return vs[-1]
    k = (len(vs) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vs[int(k)]
    return vs[f] + (k - f) * (vs[c] - vs[f])


@dataclass(frozen=True)
class MelodyRow:
    id: str
    tier: int
    tonic: str
    mode: str
    meter: str
    meter_num: int
    meter_den: int
    bars: int
    contour: str
    num_notes: int
    range_semitones: int
    largest_leap: int
    stepwise_ratio: float
    leap_ratio: float
    lowest_midi: int
    highest_midi: int
    duration_kinds: int
    interval_seq: tuple[int, ...]
    midi_path: Path
    json_path: Path


def _iter_rows(batch_dir: Path) -> Iterable[MelodyRow]:
    for json_path in sorted(batch_dir.glob("*.json")):
        if json_path.name == "manifest.json":
            continue
        try:
            md = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        melody_id = str(md.get("id") or json_path.stem)
        midi_path = json_path.with_suffix(".mid")
        if not midi_path.exists():
            continue

        m = _FILENAME_RE.match(melody_id)
        if not m:
            continue
        g = m.groupdict()

        tier = int(g["tier"])
        tonic = g["tonic"] + (g["accidental"] or "")
        mode = _normalize_mode(g["mode"])
        meter_num = int(g["meter_num"])
        meter_den = int(g["meter_den"])
        meter = f"{meter_num}/{meter_den}"
        bars = int(g["bars"])
        contour = g["contour"]

        melodic = md.get("melodic") if isinstance(md.get("melodic"), dict) else {}
        rhythmic = md.get("rhythmic") if isinstance(md.get("rhythmic"), dict) else {}
        durations = rhythmic.get("duration_histogram") if isinstance(rhythmic.get("duration_histogram"), dict) else {}
        interval_seq = md.get("file") if isinstance(md.get("file"), dict) else {}

        num_notes = int(melodic.get("num_notes") or rhythmic.get("note_count") or 0)
        range_semitones = int(melodic.get("range_semitones") or 0)
        largest_leap = int(melodic.get("largest_leap_semitones") or 0)
        stepwise_ratio = float(melodic.get("stepwise_ratio") or 0.0)
        leap_ratio = float(melodic.get("leap_ratio") or 0.0)
        lowest_midi = int(melodic.get("pitch_lowest_midi") or 0)
        highest_midi = int(melodic.get("pitch_highest_midi") or 0)
        duration_kinds = len([k for k, v in durations.items() if v])

        intervals = interval_seq.get("interval_sequence")
        if not isinstance(intervals, list) or not all(isinstance(i, (int, float)) for i in intervals):
            intervals_t = tuple()
        else:
            intervals_t = tuple(int(i) for i in intervals)

        yield MelodyRow(
            id=melody_id,
            tier=tier,
            tonic=tonic,
            mode=mode,
            meter=meter,
            meter_num=meter_num,
            meter_den=meter_den,
            bars=bars,
            contour=contour,
            num_notes=num_notes,
            range_semitones=range_semitones,
            largest_leap=largest_leap,
            stepwise_ratio=stepwise_ratio,
            leap_ratio=leap_ratio,
            lowest_midi=lowest_midi,
            highest_midi=highest_midi,
            duration_kinds=duration_kinds,
            interval_seq=intervals_t,
            midi_path=midi_path,
            json_path=json_path,
        )


def _ending_strength_from_midi(row: MelodyRow) -> dict:
    """
    Best-effort ending analysis:
    - end note pitch class equals tonic (strong) or scale degree 5 (acceptable)
    - final approach interval is stepwise (preferred)
    """
    out = {
        "ends_on_tonic": None,
        "ends_on_dominant": None,
        "final_approach_step": None,
        "final_pitch_midi": None,
        "final_interval": None,
    }
    try:
        s = m21converter.parse(str(row.midi_path))
        notes = [n for n in s.flatten().notes if getattr(n, "isNote", False)]
        if not notes:
            return out
        notes = sorted(notes, key=lambda n: float(n.offset))
        final = notes[-1]
        out["final_pitch_midi"] = int(final.pitch.midi)
        if len(notes) >= 2:
            prev = notes[-2]
            out["final_interval"] = int(final.pitch.midi) - int(prev.pitch.midi)
            out["final_approach_step"] = abs(out["final_interval"]) in (1, 2)

        scale = make_key_or_scale(row.tonic, row.mode)
        # Determine tonic and (best-effort) dominant pitch class from scale.
        tonic_pc = scale.tonic.pitchClass if hasattr(scale, "tonic") else None
        pcs = [p.pitchClass for p in scale.getPitches("C3", "C4")]
        dominant_pc = pcs[4] if len(pcs) >= 5 else None  # degree 5

        fp = final.pitch.pitchClass
        out["ends_on_tonic"] = (tonic_pc is not None) and (fp == tonic_pc)
        out["ends_on_dominant"] = (dominant_pc is not None) and (fp == dominant_pc)
        return out
    except Exception:
        return out


def _interval_ngrams(seq: tuple[int, ...], n: int) -> set[tuple[int, ...]]:
    if n <= 0 or len(seq) < n:
        return set()
    return {tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)}


def _rhythm_signature(row: MelodyRow) -> tuple[int, int, int]:
    # Coarse rhythm proxy from JSON only: (note_count_bucket, duration_kind_count, bars)
    # note_count_bucket bins by 4 notes.
    return (int(row.num_notes // 4), int(row.duration_kinds), int(row.bars))


def _shape_signature(row: MelodyRow) -> tuple:
    def cat(i: int) -> int:
        a = abs(i)
        if a == 0:
            return 0
        if a in (1, 2):
            return 1
        if a <= 5:
            return 2
        return 3

    coarse = tuple(cat(i) for i in row.interval_seq)
    return (row.contour, coarse)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--ngram-n", type=int, default=3)
    ap.add_argument("--jaccard-threshold", type=float, default=0.85)
    ap.add_argument("--max-midi-ending-checks", type=int, default=800)
    args = ap.parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.is_dir():
        raise SystemExit(f"Not a directory: {batch_dir}")

    rows = list(_iter_rows(batch_dir))
    analysis_dir = batch_dir / "_analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Coverage counters.
    counts = {
        "total_rows": len(rows),
        "by_tier": Counter(r.tier for r in rows),
        "by_key": Counter((r.tonic, r.mode) for r in rows),
        "by_meter": Counter(r.meter for r in rows),
        "by_bars": Counter(r.bars for r in rows),
        "by_contour": Counter(r.contour for r in rows),
    }

    # Distributions.
    ranges = [float(r.range_semitones) for r in rows]
    leaps = [float(r.largest_leap) for r in rows]
    step_ratios = [float(r.stepwise_ratio) for r in rows]
    notes_per_bar = [r.num_notes / max(1, r.bars) for r in rows]
    notes_per_beat = [
        r.num_notes / max(1e-9, (r.bars * _bar_len_quarter(r.meter_num, r.meter_den))) for r in rows
    ]

    def dist_summary(vals: list[float]) -> dict:
        if not vals:
            return {}
        return {
            "min": min(vals),
            "p25": _percentile(vals, 25),
            "median": _percentile(vals, 50),
            "p75": _percentile(vals, 75),
            "p95": _percentile(vals, 95),
            "max": max(vals),
            "mean": statistics.fmean(vals),
        }

    dists = {
        "range_semitones": dist_summary(ranges),
        "largest_leap_semitones": dist_summary(leaps),
        "stepwise_ratio": dist_summary(step_ratios),
        "notes_per_bar": dist_summary(notes_per_bar),
        "notes_per_beat": dist_summary(notes_per_beat),
    }

    # Outliers: flag worst 1% for a few metrics.
    outlier_rows: list[dict] = []
    thr_leap = _percentile(leaps, 99)
    thr_range = _percentile(ranges, 99)
    thr_dense = _percentile(notes_per_beat, 99)
    thr_sparse = _percentile(notes_per_beat, 1)

    for r in rows:
        npb = r.num_notes / max(1e-9, (r.bars * _bar_len_quarter(r.meter_num, r.meter_den)))
        tags = []
        if float(r.largest_leap) >= thr_leap:
            tags.append("largest_leap_p99+")
        if float(r.range_semitones) >= thr_range:
            tags.append("range_p99+")
        if npb >= thr_dense:
            tags.append("density_p99+")
        if npb <= thr_sparse:
            tags.append("density_p01-")
        if tags:
            outlier_rows.append(
                {
                    "id": r.id,
                    "tier": r.tier,
                    "key": f"{r.tonic} {r.mode}",
                    "meter": r.meter,
                    "bars": r.bars,
                    "contour": r.contour,
                    "num_notes": r.num_notes,
                    "range_semitones": r.range_semitones,
                    "largest_leap": r.largest_leap,
                    "stepwise_ratio": round(r.stepwise_ratio, 3),
                    "notes_per_beat": round(npb, 3),
                    "tags": "|".join(tags),
                }
            )

    # Ending strength: sample up to N MIDIs (avoid being too slow).
    ending_stats = defaultdict(int)
    checked = 0
    for r in rows[: int(args.max_midi_ending_checks)]:
        e = _ending_strength_from_midi(r)
        if e["ends_on_tonic"] is None:
            continue
        checked += 1
        if e["ends_on_tonic"]:
            ending_stats["ends_on_tonic"] += 1
        if e["ends_on_dominant"]:
            ending_stats["ends_on_dominant"] += 1
        if e["final_approach_step"] is True:
            ending_stats["final_approach_step"] += 1
    ending_summary = {
        "checked_midis": checked,
        "ends_on_tonic_ratio": (ending_stats["ends_on_tonic"] / checked) if checked else None,
        "ends_on_dominant_ratio": (ending_stats["ends_on_dominant"] / checked) if checked else None,
        "final_approach_step_ratio": (ending_stats["final_approach_step"] / checked) if checked else None,
    }

    # Near-duplicates within buckets.
    buckets: dict[tuple, list[MelodyRow]] = defaultdict(list)
    for r in rows:
        buckets[(r.tier, r.meter, r.bars, r.contour)].append(r)

    near_dupes: list[dict] = []
    n = int(args.ngram_n)
    thr = float(args.jaccard_threshold)

    for bkey, items in buckets.items():
        if len(items) < 2:
            continue

        # Index by exact interval sequence first (cheap).
        by_interval = defaultdict(list)
        for r in items:
            by_interval[r.interval_seq].append(r)

        for seq, group in by_interval.items():
            if len(group) >= 2 and len(seq) > 0:
                # Exact-interval duplicates; check rhythm signature similarity.
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        a, b = group[i], group[j]
                        if _rhythm_signature(a) == _rhythm_signature(b):
                            near_dupes.append(
                                {
                                    "a_id": a.id,
                                    "b_id": b.id,
                                    "bucket": "|".join(map(str, bkey)),
                                    "reason": "identical_interval_seq + same_rhythm_signature",
                                    "score": 1.0,
                                }
                            )

        # Jaccard on n-grams (bounded O(k^2) per bucket; buckets are small enough here).
        ngrams = {r.id: _interval_ngrams(r.interval_seq, n) for r in items}
        ids = [r.id for r in items]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                sa, sb = ngrams[a], ngrams[b]
                if not sa or not sb:
                    continue
                inter = len(sa & sb)
                union = len(sa | sb)
                if union == 0:
                    continue
                jac = inter / union
                if jac >= thr and _shape_signature(next(r for r in items if r.id == a)) == _shape_signature(
                    next(r for r in items if r.id == b)
                ):
                    near_dupes.append(
                        {
                            "a_id": a,
                            "b_id": b,
                            "bucket": "|".join(map(str, bkey)),
                            "reason": f"interval_{n}gram_jaccard>= {thr:g} + same_shape_signature",
                            "score": round(jac, 3),
                        }
                    )

    # Write artifacts.
    summary = {
        "batch_dir": str(batch_dir),
        "counts": {
            "total": counts["total_rows"],
            "by_tier": dict(counts["by_tier"]),
            "by_meter": dict(counts["by_meter"]),
            "by_bars": dict(counts["by_bars"]),
            "by_contour": dict(counts["by_contour"]),
        },
        "key_mode_coverage_count": len(counts["by_key"]),
        "distributions": dists,
        "outliers_count": len(outlier_rows),
        "near_duplicates_count": len(near_dupes),
        "ending_summary_sampled": ending_summary,
    }

    (analysis_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # outliers.csv
    if outlier_rows:
        with (analysis_dir / "outliers.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(outlier_rows[0].keys()))
            w.writeheader()
            w.writerows(outlier_rows)
    else:
        (analysis_dir / "outliers.csv").write_text("id\n", encoding="utf-8")

    # near_duplicates.csv
    if near_dupes:
        with (analysis_dir / "near_duplicates.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["a_id", "b_id", "bucket", "reason", "score"])
            w.writeheader()
            w.writerows(near_dupes)
    else:
        (analysis_dir / "near_duplicates.csv").write_text("a_id,b_id,bucket,reason,score\n", encoding="utf-8")

    # summary.md
    md = []
    md.append(f"## Deep analysis summary\n")
    md.append(f"- **Batch**: `{batch_dir}`")
    md.append(f"- **Melodies analyzed**: **{counts['total_rows']}**")
    md.append(f"- **Near-duplicate pairs flagged**: **{len(near_dupes)}**")
    md.append(f"- **Outlier rows**: **{len(outlier_rows)}**\n")

    md.append("### Composition\n")
    md.append(f"- **By tier**: {dict(counts['by_tier'])}")
    md.append(f"- **By meter**: {dict(counts['by_meter'])}")
    md.append(f"- **By bars**: {dict(counts['by_bars'])}")
    md.append(f"- **By contour**: top 10 {counts['by_contour'].most_common(10)}")
    md.append(f"- **Key×mode combos**: {len(counts['by_key'])}\n")

    md.append("### Distributions (overall)\n")
    for k, v in dists.items():
        if not v:
            continue
        md.append(
            f"- **{k}**: min {v['min']:.3g}, p25 {v['p25']:.3g}, median {v['median']:.3g}, "
            f"p75 {v['p75']:.3g}, p95 {v['p95']:.3g}, max {v['max']:.3g}, mean {v['mean']:.3g}"
        )
    md.append("")

    md.append("### Ending strength (sampled)\n")
    md.append(f"- **MIDIs checked**: {ending_summary['checked_midis']}")
    md.append(f"- **Ends on tonic ratio**: {ending_summary['ends_on_tonic_ratio']}")
    md.append(f"- **Ends on dominant ratio**: {ending_summary['ends_on_dominant_ratio']}")
    md.append(f"- **Final approach step ratio**: {ending_summary['final_approach_step_ratio']}\n")

    (analysis_dir / "summary.md").write_text("\n".join(md).strip() + "\n", encoding="utf-8")

    print(f"Wrote analysis to: {analysis_dir}")
    print(f"- summary.json")
    print(f"- summary.md")
    print(f"- outliers.csv")
    print(f"- near_duplicates.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

