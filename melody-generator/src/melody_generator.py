from __future__ import annotations

"""
Orchestrates the melody generation pipeline (template → rhythm → pitch → validate → dedupe).

This module is the high-level "glue" that wires together the lower-level units.
"""

import random

from src.contour_engine import get_contour_curve
from src.diversity_checker import DiversityChecker
from src.models import Melody, Note, TierConfig
from src.pitch_generator import generate_pitch_sequence
from src.rhythm_generator import generate_rhythm
from src.validator import validate_melody

from music21 import key as m21key
from music21 import pitch as m21pitch


def _pitch_class_for_scale_degree(key_tonic: str, key_mode: str, degree: int) -> int:
    k = m21key.Key(key_tonic, key_mode)
    p = k.pitchFromDegree(degree)
    return int(p.pitchClass)


def _nearest_pitch_with_pitch_class(
    *,
    target_midi: int,
    pitch_class: int,
    allowed_range: tuple[int, int],
) -> int:
    lo, hi = allowed_range
    best = None
    best_dist = 10**9
    for midi in range(lo, hi + 1):
        p = m21pitch.Pitch()
        p.midi = midi
        if p.pitchClass != pitch_class:
            continue
        dist = abs(midi - target_midi)
        if dist < best_dist:
            best_dist = dist
            best = midi
    if best is None:
        raise RuntimeError("No pitch found for pitch class in range")
    return int(best)


def _force_ending_tonic(pitches: list[int], key_tonic: str, key_mode: str, tier_config: TierConfig) -> list[int]:
    if not pitches:
        return pitches
    tonic_pc = _pitch_class_for_scale_degree(key_tonic, key_mode, 1)
    target = _nearest_pitch_with_pitch_class(target_midi=pitches[-1], pitch_class=tonic_pc, allowed_range=(57, 81))

    # Ensure the final interval is allowed; if not, try other octave choices.
    prev = pitches[-2] if len(pitches) >= 2 else target
    candidates = []
    for midi in range(57, 82):
        p = m21pitch.Pitch()
        p.midi = midi
        if p.pitchClass != tonic_pc:
            continue
        interval = abs(midi - prev)
        if interval == 0:
            continue
        if interval in tier_config.forbidden_intervals:
            continue
        if tier_config.allowed_intervals_semitones and interval not in tier_config.allowed_intervals_semitones:
            continue
        candidates.append(midi)

    if candidates:
        # pick closest to our original target
        best = min(candidates, key=lambda x: abs(x - target))
        pitches[-1] = int(best)
    else:
        pitches[-1] = int(target)
    return pitches


def _make_melody_id(
    *,
    tier_code: str,
    key_tonic: str,
    key_mode: str,
    meter: str,
    bar_count: int,
    contour_type: str,
    sequence_num: int,
) -> str:
    mode = {"major": "maj", "minor": "min"}.get(key_mode, key_mode[:3])
    meter_code = meter.replace("/", "")
    return f"{tier_code}_{key_tonic}{mode}_{meter_code}_{bar_count}bar_{contour_type}_{sequence_num:04d}"


def _build_notes(pitches: list[int], rhythm: list[tuple[str, float]], meter: str) -> list[Note]:
    beats_per_bar = {"4/4": 4.0, "3/4": 3.0, "2/4": 2.0}[meter]
    notes: list[Note] = []
    beat_in_bar = 0.0
    bar_number = 1

    for midi, (dur_name, dur_beats) in zip(pitches, rhythm):
        notes.append(Note(midi_pitch=midi, duration=dur_name, beat_position=beat_in_bar, bar_number=bar_number))
        beat_in_bar += float(dur_beats)
        while beat_in_bar >= beats_per_bar - 1e-9:
            beat_in_bar -= beats_per_bar
            bar_number += 1

    return notes


def generate_one_melody(
    tier_config: TierConfig,
    template: dict,
    *,
    batch_seed: int,
    sequence_num: int,
    diversity_checker: DiversityChecker,
    rng: random.Random | None = None,
    max_attempts: int = 20,
) -> Melody | None:
    """
    Try up to `max_attempts` times to produce a valid, non-duplicate melody.
    Returns None if it gives up.
    """

    melody_seed = hash((batch_seed, template.get("id", ""), sequence_num))
    base_rng = rng or random.Random(melody_seed)

    for attempt in range(max_attempts):
        # Make attempts explore different random branches deterministically.
        attempt_seed = hash((melody_seed, attempt, base_rng.random()))
        local_rng = random.Random(attempt_seed)

        key_choice = local_rng.choice(tier_config.keys)
        key_tonic = key_choice["tonic"]
        key_mode = key_choice["mode"]

        meter = local_rng.choice(tier_config.meters)
        bar_count = local_rng.choice(template.get("bar_counts", tier_config.bar_counts))
        contour_type = local_rng.choice(tier_config.contour_types)
        cadence_type = template.get("cadence_type") or local_rng.choice(tier_config.cadence_types)

        allowed_durations = tier_config.durations_normal
        rhythm = generate_rhythm(meter, bar_count, allowed_durations, local_rng)
        rhythm_durations = [d for d, _b in rhythm]

        contour_targets = get_contour_curve(contour_type, len(rhythm))

        # Start pitch: choose a pitch class matching an allowed start degree.
        start_degree = local_rng.choice(template.get("start_degree_options", tier_config.start_scale_degrees))
        start_pc = _pitch_class_for_scale_degree(key_tonic, key_mode, int(start_degree))
        starting_pitch = _nearest_pitch_with_pitch_class(
            target_midi=69, pitch_class=start_pc, allowed_range=(57, 81)
        )
        pitches = generate_pitch_sequence(
            key_tonic=key_tonic,
            key_mode=key_mode,
            contour_targets=contour_targets,
            rhythm_durations=rhythm_durations,
            tier_config=tier_config,
            rng=local_rng,
            starting_pitch=starting_pitch,
        )
        # v1 enforcement for T1: ensure it can end on tonic if required.
        if 1 in tier_config.end_scale_degrees:
            pitches = _force_ending_tonic(pitches, key_tonic, key_mode, tier_config)

        notes = _build_notes(pitches, rhythm, meter)

        melody_id = _make_melody_id(
            tier_code=tier_config.code,
            key_tonic=key_tonic,
            key_mode=key_mode,
            meter=meter,
            bar_count=bar_count,
            contour_type=contour_type,
            sequence_num=sequence_num,
        )

        melody = Melody(
            melody_id=melody_id,
            notes=notes,
            tier=int(tier_config.code.replace("T", "")) if tier_config.code.startswith("T") else 1,
            key_tonic=key_tonic,
            key_mode=key_mode,
            meter=meter,
            bar_count=bar_count,
            contour_type=contour_type,
            cadence_type=cadence_type,
            seed=int(melody_seed),
            template_id=str(template.get("id", "")),
        )

        passed, _violations = validate_melody(melody, tier_config)
        if not passed:
            continue

        if diversity_checker.is_too_similar(melody):
            continue

        diversity_checker.register(melody)
        return melody

    return None

