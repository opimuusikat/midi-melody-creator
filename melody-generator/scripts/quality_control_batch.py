"""
Quality control for a generated melody batch.

This script validates that each MIDI/JSON pair is internally consistent and
musically sane for the monophonic exercise dataset.

Usage:
  python scripts/quality_control_batch.py --batch-dir output/batch_2500_modes_v2

OpiMuusikat dictation (strict MIDI + minimum JSON), see docs/opi-dictation-integration-rulebook.md:
  python scripts/quality_control_batch.py --batch-dir output/my_batch --dictation-mode
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow running as `python scripts/...` without installing package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from music21 import converter as m21converter  # type: ignore
from music21 import note as m21note  # type: ignore
from music21 import stream as m21stream  # type: ignore
from music21 import tempo as m21tempo  # type: ignore

from src.music21_utils import make_key_or_scale


_FILENAME_RE = re.compile(
    r"^T(?P<tier>[123])_"
    r"(?P<tonic>[A-G])(?P<accidental>b|#)?"
    r"(?P<mode>maj|min|major|minor|dor|phr|lyd|mix|dorian|phrygian|lydian|mixolydian)_"
    r"(?P<meter_num>\d+)(?P<meter_den>\d+)_"
    r"(?P<bars>\d+)bar_"
    # Contour names can include hyphens (e.g. "inverted-arch").
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


def _bar_length_quarter(meter_num: int, meter_den: int) -> float:
    return float(meter_num) * (4.0 / float(meter_den))


def _is_close(a: float, b: float, *, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


# OpiMuusikat dictation v1: whole / half / quarter / eighth only (quarterLength).
_DICTATION_ALLOWED_QUARTER_LENGTHS: tuple[float, ...] = (4.0, 2.0, 1.0, 0.5)
_DICTATION_METERS_V1: frozenset[str] = frozenset({"2/4", "3/4", "4/4"})


def _dictation_quarter_length_allowed(dur: float, *, tol: float = 1e-4) -> bool:
    return any(abs(dur - a) <= tol for a in _DICTATION_ALLOWED_QUARTER_LENGTHS)


def _resolve_meter_bars_dictation(
    parsed: dict | None, md: dict | None
) -> tuple[int, int, int] | None:
    """Return (meter_num, meter_den, bar_count) from filename parse or JSON rhythmic."""
    if parsed:
        return int(parsed["meter_num"]), int(parsed["meter_den"]), int(parsed["bars"])
    if isinstance(md, dict):
        rh = md.get("rhythmic")
        if isinstance(rh, dict):
            m = rh.get("meter")
            bc = rh.get("bar_count")
            if isinstance(m, str) and "/" in m and isinstance(bc, int):
                parts = m.split("/")
                if len(parts) == 2:
                    try:
                        return int(parts[0]), int(parts[1]), bc
                    except ValueError:
                        return None
    return None


def _opi_dictation_rulebook_issues(
    *,
    notes: list[m21note.Note],
    parsed: dict | None,
    md: dict | None,
) -> list[Issue]:
    """
    Enforce docs/opi-dictation-integration-rulebook.md (MIDI + minimum JSON).

    Requires monophonic note stream (chords/overlaps checked elsewhere).
    """
    issues: list[Issue] = []

    if md is not None:
        rh = md.get("rhythmic") if isinstance(md.get("rhythmic"), dict) else None
        if not isinstance(rh, dict):
            issues.append(
                Issue(
                    "FAIL",
                    "dictation.json.rhythmic.missing",
                    "dictation-mode requires JSON.rhythmic object with meter and bar_count.",
                )
            )
        else:
            if not rh.get("meter"):
                issues.append(
                    Issue("FAIL", "dictation.json.rhythmic.meter_missing", "JSON rhythmic.meter is required.")
                )
            bc = rh.get("bar_count")
            if not isinstance(bc, int) or not (1 <= bc <= 4):
                issues.append(
                    Issue(
                        "FAIL",
                        "dictation.json.rhythmic.bar_count_invalid",
                        "JSON rhythmic.bar_count must be an integer 1..4.",
                    )
                )

        diff = md.get("difficulty") if isinstance(md.get("difficulty"), dict) else None
        if not isinstance(diff, dict):
            issues.append(
                Issue("FAIL", "dictation.json.difficulty.missing", "dictation-mode requires JSON.difficulty.tier.")
            )
        else:
            tier = diff.get("tier")
            if not isinstance(tier, int) or tier not in (1, 2, 3):
                issues.append(
                    Issue(
                        "FAIL",
                        "dictation.json.difficulty.tier_invalid",
                        "JSON difficulty.tier must be an integer 1..3.",
                    )
                )

        if isinstance(md.get("rhythmic"), dict) and isinstance(md.get("difficulty"), dict):
            rh = md["rhythmic"]
            if isinstance(rh.get("bar_count"), int) and isinstance(diff.get("tier"), int):
                # Filename vs JSON consistency when both exist
                if parsed:
                    fn_bars = int(parsed["bars"])
                    if rh["bar_count"] != fn_bars:
                        issues.append(
                            Issue(
                                "FAIL",
                                "dictation.json.bars.filename_mismatch",
                                f'JSON rhythmic.bar_count {rh["bar_count"]} != filename bars {fn_bars}.',
                            )
                        )
                    fn_meter = f'{int(parsed["meter_num"])}/{int(parsed["meter_den"])}'
                    if rh.get("meter") and str(rh["meter"]) != fn_meter:
                        issues.append(
                            Issue(
                                "FAIL",
                                "dictation.json.meter.filename_mismatch",
                                f'JSON rhythmic.meter "{rh.get("meter")}" != filename meter {fn_meter}.',
                            )
                        )

    resolved = _resolve_meter_bars_dictation(parsed, md)
    if resolved is None:
        issues.append(
            Issue(
                "FAIL",
                "dictation.meter_unresolved",
                "Could not resolve meter/bar_count from filename or JSON (need one source).",
            )
        )
        return issues

    meter_num, meter_den, bars = resolved
    meter_s = f"{meter_num}/{meter_den}"
    if meter_s not in _DICTATION_METERS_V1:
        issues.append(
            Issue(
                "FAIL",
                "dictation.meter.not_allowed_v1",
                f"Meter must be one of 2/4, 3/4, 4/4 (got {meter_s}).",
            )
        )

    if not (1 <= bars <= 4):
        issues.append(
            Issue("FAIL", "dictation.bar_count.out_of_range", f"bar_count must be 1..4 (got {bars}).")
        )

    bar_len = _bar_length_quarter(meter_num, meter_den)
    expected_total = bars * bar_len

    items = sorted(((float(n.offset), float(n.quarterLength)) for n in notes), key=lambda x: x[0])
    tol_gap = 1e-3
    eps_bar = 1e-9

    for i, (off, dur) in enumerate(items):
        if not _dictation_quarter_length_allowed(dur):
            issues.append(
                Issue(
                    "FAIL",
                    "dictation.duration.not_whitelisted",
                    f"Note {i} quarterLength {dur} is not whole/half/quarter/eighth.",
                )
            )

        a = int(math.floor((off + eps_bar) / bar_len))
        b = int(math.floor((off + dur - eps_bar) / bar_len))
        if a != b:
            issues.append(
                Issue(
                    "FAIL",
                    "dictation.bar_crossing",
                    f"Note {i} crosses a bar boundary (offset={off:.3f}q, dur={dur:.3f}q, bar_len={bar_len}).",
                )
            )

    if items:
        if items[0][0] > tol_gap:
            issues.append(
                Issue(
                    "FAIL",
                    "dictation.contiguous.leading_gap",
                    f"First note starts at {items[0][0]:.3f}q (expected 0).",
                )
            )
        for i in range(1, len(items)):
            prev_off, prev_dur = items[i - 1]
            prev_end = prev_off + prev_dur
            off, _dur = items[i]
            if off > prev_end + tol_gap:
                issues.append(
                    Issue(
                        "FAIL",
                        "dictation.contiguous.gap",
                        f"Gap between notes {i - 1} and {i}: {off - prev_end:.3f}q.",
                    )
                )
            if off < prev_end - tol_gap:
                issues.append(
                    Issue(
                        "FAIL",
                        "dictation.contiguous.overlap",
                        f"Overlap between notes {i - 1} and {i}: {prev_end - off:.3f}q.",
                    )
                )

    if not _is_close(float(_note_end_time_quarter_from_items(items)), expected_total, tol=1e-2):
        issues.append(
            Issue(
                "FAIL",
                "dictation.fill.mismatch",
                f"Timeline fill {float(_note_end_time_quarter_from_items(items)):.3f}q != expected {expected_total:.3f}q "
                f"({bars} bars of {meter_s}).",
            )
        )

    return issues


def _note_end_time_quarter_from_items(items: list[tuple[float, float]]) -> float:
    if not items:
        return 0.0
    return max(off + dur for off, dur in items)


@dataclass(frozen=True)
class Issue:
    severity: str  # "FAIL" | "WARN"
    code: str
    message: str


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_midi_notes(s: m21stream.Stream) -> list[m21note.Note]:
    # Flatten across parts/voices; ignore rests. Chords will appear as Chord,
    # which we detect separately.
    return [n for n in s.flatten().notes if isinstance(n, m21note.Note)]


def _note_end_time_quarter(s: m21stream.Stream) -> float:
    """
    Compute end time from musical events only.

    `Stream.highestTime` can be misleading for MIDI imports (it may reflect
    implied measure padding or end-of-track timing rather than the last note end).
    """
    flat = s.flatten()
    ends: list[float] = []
    for el in flat.notes:
        try:
            onset = float(el.offset)
            dur = float(el.quarterLength)
            ends.append(onset + dur)
        except Exception:
            continue
    return max(ends) if ends else float(flat.highestTime)


def _detect_polyphony_or_overlaps(s: m21stream.Stream) -> tuple[bool, bool]:
    """Return (has_chords, has_overlaps) within the flattened note stream."""
    flat = s.flatten()
    has_chords = any(el.classes and "Chord" in el.classes for el in flat.notes)
    notes = _collect_midi_notes(s)
    if not notes:
        return has_chords, False

    # Sort by onset offset.
    items = sorted(((float(n.offset), float(n.quarterLength)) for n in notes), key=lambda x: x[0])
    last_end = items[0][0] + items[0][1]
    has_overlaps = False
    for onset, dur in items[1:]:
        if onset < last_end - 1e-6:
            has_overlaps = True
            break
        last_end = max(last_end, onset + dur)
    return has_chords, has_overlaps


def _extract_tempo_bpm(s: m21stream.Stream) -> float | None:
    marks = list(s.recurse().getElementsByClass(m21tempo.MetronomeMark))
    if not marks:
        return None
    for m in marks:
        try:
            bpm = float(m.number)
            if math.isfinite(bpm) and bpm > 0:
                return bpm
        except Exception:
            continue
    return None


def qc_one(midi_path: Path, json_path: Path | None, *, dictation_mode: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    stem = midi_path.stem

    m = _FILENAME_RE.match(stem)
    if not m:
        issues.append(Issue("FAIL", "filename.parse", "Filename does not match expected pattern."))
        parsed = None
    else:
        parsed = m.groupdict()

    md = _load_json(json_path) if json_path else None
    if json_path and md is None:
        issues.append(Issue("FAIL", "json.parse", "JSON sidecar exists but could not be parsed."))
    if not json_path:
        issues.append(Issue("FAIL", "json.missing", "Missing JSON sidecar for MIDI."))

    try:
        s = m21converter.parse(str(midi_path))
    except Exception as e:
        issues.append(Issue("FAIL", "midi.parse", f"Could not parse MIDI: {e!r}"))
        return issues

    notes = _collect_midi_notes(s)
    if not notes:
        issues.append(Issue("FAIL", "midi.empty", "No Note events found in MIDI."))
        return issues

    has_chords, has_overlaps = _detect_polyphony_or_overlaps(s)
    if has_chords:
        issues.append(Issue("FAIL", "midi.polyphony.chords", "Chord events found (expected monophonic)."))
    if has_overlaps:
        issues.append(Issue("FAIL", "midi.polyphony.overlap", "Overlapping notes found (expected monophonic)."))

    total_q = float(_note_end_time_quarter(s))
    if total_q <= 0:
        issues.append(Issue("FAIL", "midi.duration.zero", "Total duration is zero or negative."))

    # Filename-driven checks.
    if parsed:
        tier = int(parsed["tier"])
        tonic = parsed["tonic"] + (parsed["accidental"] or "")
        mode = _normalize_mode(parsed["mode"])
        meter_num = int(parsed["meter_num"])
        meter_den = int(parsed["meter_den"])
        bars = int(parsed["bars"])
        contour = parsed["contour"]

        expected_total = bars * _bar_length_quarter(meter_num, meter_den)
        if not _is_close(total_q, expected_total, tol=1e-3):
            issues.append(
                Issue(
                    "WARN",
                    "midi.duration.mismatch",
                    f"Total duration {total_q:.3f}q != expected {expected_total:.3f}q from {bars} bars of {meter_num}/{meter_den}.",
                )
            )

        # Notes-in-scale check (best-effort; tolerate a small number of out-of-scale notes).
        try:
            scale_or_key = make_key_or_scale(tonic, mode)
            pcs = {p.pitchClass for p in scale_or_key.getPitches("C3", "C4")}
            out_of_scale = sum(1 for n in notes if n.pitch.pitchClass not in pcs)
            ratio = out_of_scale / max(1, len(notes))
            if out_of_scale > 0 and ratio > 0.02:
                issues.append(
                    Issue(
                        "WARN",
                        "tonal.out_of_scale",
                        f"{out_of_scale}/{len(notes)} notes ({ratio:.1%}) are outside {tonic} {mode}.",
                    )
                )
        except Exception:
            issues.append(Issue("WARN", "tonal.scale_check_failed", "Could not run notes-in-scale check."))

        # JSON consistency checks.
        if md:
            if md.get("id") != stem:
                issues.append(Issue("FAIL", "json.id.mismatch", f'JSON id "{md.get("id")}" != "{stem}".'))

            tonal = md.get("tonal") if isinstance(md.get("tonal"), dict) else {}
            if tonal.get("key") and str(tonal.get("key")) != tonic:
                issues.append(
                    Issue(
                        "WARN",
                        "json.tonal.key.mismatch",
                        f'JSON tonal.key "{tonal.get("key")}" != filename tonic "{tonic}".',
                    )
                )
            if tonal.get("mode") and _normalize_mode(str(tonal.get("mode"))) != mode:
                issues.append(
                    Issue(
                        "WARN",
                        "json.tonal.mode.mismatch",
                        f'JSON tonal.mode "{tonal.get("mode")}" != filename mode "{mode}".',
                    )
                )

            difficulty = md.get("difficulty") if isinstance(md.get("difficulty"), dict) else {}
            if isinstance(difficulty.get("tier"), int) and difficulty.get("tier") != tier:
                issues.append(
                    Issue(
                        "WARN",
                        "json.tier.mismatch",
                        f'JSON difficulty.tier {difficulty.get("tier")} != filename tier {tier}.',
                    )
                )

            melodic = md.get("melodic") if isinstance(md.get("melodic"), dict) else {}
            if melodic.get("contour_type") and str(melodic.get("contour_type")) != contour:
                issues.append(
                    Issue(
                        "WARN",
                        "json.contour.mismatch",
                        f'JSON melodic.contour_type "{melodic.get("contour_type")}" != filename contour "{contour}".',
                    )
                )

            rhythmic = md.get("rhythmic") if isinstance(md.get("rhythmic"), dict) else {}
            if rhythmic.get("meter") and str(rhythmic.get("meter")) != f"{meter_num}/{meter_den}":
                issues.append(
                    Issue(
                        "WARN",
                        "json.meter.mismatch",
                        f'JSON rhythmic.meter "{rhythmic.get("meter")}" != "{meter_num}/{meter_den}".',
                    )
                )
            if isinstance(rhythmic.get("bar_count"), int) and rhythmic.get("bar_count") != bars:
                issues.append(
                    Issue(
                        "WARN",
                        "json.bars.mismatch",
                        f'JSON rhythmic.bar_count {rhythmic.get("bar_count")} != {bars}.',
                    )
                )

    bpm = _extract_tempo_bpm(s)
    if bpm is None:
        issues.append(Issue("WARN", "midi.tempo.missing", "No tempo mark found in MIDI."))
    elif bpm != 90.0:
        issues.append(Issue("WARN", "midi.tempo.unexpected", f"Tempo is {bpm:g} bpm (expected 90)."))

    # Basic pitch sanity
    pitches = [int(n.pitch.midi) for n in notes]
    lo, hi = min(pitches), max(pitches)
    if lo < 36 or hi > 96:
        issues.append(Issue("WARN", "midi.pitch.range", f"Pitch range is {lo}..{hi} MIDI (unusual)."))

    if dictation_mode:
        issues.extend(_opi_dictation_rulebook_issues(notes=notes, parsed=parsed, md=md))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True, help="Path to output batch directory")
    ap.add_argument("--max-examples", type=int, default=20, help="Max examples to print per issue code")
    ap.add_argument(
        "--dictation-mode",
        action="store_true",
        help="Enforce OpiMuusikat dictation v1 contract (see docs/opi-dictation-integration-rulebook.md).",
    )
    args = ap.parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.exists() or not batch_dir.is_dir():
        raise SystemExit(f"Not a directory: {batch_dir}")

    midi_files = sorted(batch_dir.glob("*.mid"))
    if not midi_files:
        print("No .mid files found.")
        return 2

    totals = {"files": 0, "fail_files": 0, "warn_files": 0}
    by_code: dict[str, dict] = {}

    for midi_path in midi_files:
        totals["files"] += 1
        json_path = midi_path.with_suffix(".json")
        issues = qc_one(
            midi_path,
            json_path if json_path.exists() else None,
            dictation_mode=bool(args.dictation_mode),
        )
        if not issues:
            continue

        has_fail = any(i.severity == "FAIL" for i in issues)
        has_warn = any(i.severity == "WARN" for i in issues)
        if has_fail:
            totals["fail_files"] += 1
        elif has_warn:
            totals["warn_files"] += 1

        for i in issues:
            entry = by_code.setdefault(
                i.code, {"severity": i.severity, "count": 0, "message": i.message, "examples": []}
            )
            entry["count"] += 1
            if len(entry["examples"]) < int(args.max_examples):
                entry["examples"].append(midi_path.name)

    print(f"Batch: {batch_dir}")
    if args.dictation_mode:
        print("Mode: dictation (OpiMuusikat v1 — see docs/opi-dictation-integration-rulebook.md)")
    print(f"Files: {totals['files']} | FAIL files: {totals['fail_files']} | WARN-only files: {totals['warn_files']}")

    if not by_code:
        print("QC: clean (no issues found).")
        return 0

    # Print FAILs first, then WARNs, by descending count.
    def _sort_key(item: tuple[str, dict]) -> tuple[int, int]:
        code, e = item
        sev_rank = 0 if e["severity"] == "FAIL" else 1
        return (sev_rank, -int(e["count"]))

    for code, e in sorted(by_code.items(), key=_sort_key):
        print(f"- {e['severity']} {code}: {e['count']}  ({e['message']})")
        for ex in e["examples"]:
            print(f"    - {ex}")

    return 1 if totals["fail_files"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

