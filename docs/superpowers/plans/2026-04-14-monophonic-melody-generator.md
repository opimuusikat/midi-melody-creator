# Monophonic Melody Generator (MIDI + JSON) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Python CLI tool that generates batches of monophonic MIDI melodies (A3–A5 only) plus per-melody metadata JSON, with tiered rule validation, deduplication, and deterministic regeneration by seed; publish to a new GitHub repo.

**Architecture:** Three-layer generator: template selection → constrained stochastic fill (rhythm then pitch) → validation + diversity acceptance. Config is YAML-driven per tier, with output as `.mid` + `.json` per melody plus a batch manifest.

**Tech Stack:** Python 3.10+, `music21==9.1.0`, `pretty_midi==0.2.10`, `numpy`, `pyyaml`, `pytest`.

---

## Scope notes (v1)
- **Meters:** only `4/4`, `3/4`, `2/4`. (**6/8 removed** across configs, rhythm rules, tests, quotas.)
- **Tempo:** fixed **90 BPM** in MIDI export (website can change playback tempo).
- **No rests** in v1.
- **Primary deliverable:** generator code + configs + tests. Generated output `output/` stays gitignored until we intentionally publish a batch.

## Planned repo structure (created under workspace root)
Create a project folder `melody-generator/` with:

```
melody-generator/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   ├── tier1.yaml
│   ├── tier2.yaml
│   ├── tier3.yaml
│   ├── key_profiles.yaml
│   └── batch_config.yaml
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── template_library.py
│   ├── contour_engine.py
│   ├── pitch_generator.py
│   ├── rhythm_generator.py
│   ├── cadence_rules.py
│   ├── validator.py
│   ├── diversity_checker.py
│   ├── difficulty_scorer.py
│   ├── metadata_extractor.py
│   ├── midi_exporter.py
│   └── melody_generator.py
├── scripts/
│   ├── generate_batch.py
│   ├── validate_batch.py
│   └── analyze_diversity.py
├── tests/
│   ├── test_models.py
│   ├── test_template_library.py
│   ├── test_contour_engine.py
│   ├── test_rhythm_generator.py
│   ├── test_pitch_generator.py
│   ├── test_cadence_rules.py
│   ├── test_validator.py
│   ├── test_diversity_checker.py
│   ├── test_difficulty_scorer.py
│   ├── test_end_to_end.py
│   └── helpers.py
└── output/
    └── batch_001/
```

---

### Task 0: Project scaffold + dependency setup

**Files:**
- Create: `melody-generator/README.md`
- Create: `melody-generator/requirements.txt`
- Create: `melody-generator/.gitignore`
- Create directories: `melody-generator/config/`, `melody-generator/src/`, `melody-generator/scripts/`, `melody-generator/tests/`, `melody-generator/output/`
- Create: `melody-generator/src/__init__.py`

- [ ] **Step 1: Write failing test (project imports exist)**

Create `melody-generator/tests/test_smoke_imports.py`:

```python
def test_imports_smoke():
    import src.models  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `melody-generator/`):
- `python -m pytest -q`

Expected: FAIL (module/file not found).

- [ ] **Step 3: Create minimal files + package layout**

Create the folders/files listed above and an empty `src/models.py` file.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q`

Expected: PASS.

---

### Task 1: Data models (`src/models.py`)

**Files:**
- Create: `melody-generator/src/models.py`
- Test: `melody-generator/tests/test_models.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_models.py`:

```python
from src.models import Note, Melody, TierConfig


def test_models_construct():
    n = Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1)
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
        notes=[n],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=123,
        template_id="T1_template",
    )
    c = TierConfig(
        name="Beginner",
        code="T1",
        keys=[{"tonic": "C", "mode": "major"}],
        bar_counts=[1],
        meters=["4/4"],
        durations_normal=["quarter"],
        durations_6_8=[],
        range_semitones_max=12,
        chromatic_allowed=False,
        chromatic_ratio_max=0.0,
        allowed_intervals_semitones=[1, 2],
        forbidden_intervals=[],
        max_consecutive_leaps=1,
        leap_compensation_required=True,
        stepwise_ratio_min=0.7,
        start_scale_degrees=[1],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch"],
        leading_tone_resolution_required=True,
    )
    assert m.notes[0].midi_pitch == 60
    assert c.code == "T1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_models.py`

Expected: FAIL (cannot import names / missing classes).

- [ ] **Step 3: Implement minimal dataclasses**

Implement dataclasses per source spec section §7 (with `durations_6_8` kept as a field but unused in v1).

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_models.py`

Expected: PASS.

---

### Task 2: YAML config loader utilities (small helper)

**Files:**
- Create: `melody-generator/src/config_loader.py`
- Test: `melody-generator/tests/test_config_loader.py`
- Create: `melody-generator/config/tier1.yaml`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_config_loader.py`:

```python
from pathlib import Path

from src.config_loader import load_tier_config


def test_load_tier1_yaml_to_dataclass(tmp_path: Path):
    yaml_text = """
name: "Beginner"
code: "T1"
keys:
  - {tonic: "C", mode: "major"}
bar_counts: [1, 2]
meters: ["4/4", "3/4", "2/4"]
durations_normal: ["quarter", "eighth"]
durations_6_8: []
range_semitones_max: 12
allowed_scale_degrees: [1,2,3,4,5,6,7]
chromatic_allowed: false
chromatic_ratio_max: 0.0
allowed_intervals_semitones: [1,2,3,4,5,7]
forbidden_intervals: [6,10,11]
max_consecutive_leaps: 1
leap_compensation_required: true
stepwise_ratio_min: 0.70
start_scale_degrees: [1,3,5]
end_scale_degrees: [1]
cadence_types: ["authentic"]
contour_types: ["arch", "ascending", "descending"]
leading_tone_resolution_required: true
prefer_chord_tones_on_strong_beats: true
arch_contour_preference: 0.60
"""
    p = tmp_path / "tier1.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_tier_config(p)
    assert cfg.code == "T1"
    assert "4/4" in cfg.meters
    assert cfg.chromatic_allowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_config_loader.py`

Expected: FAIL (module/function missing).

- [ ] **Step 3: Implement minimal loader**

Implement `load_tier_config(path: Path) -> TierConfig` using `pyyaml.safe_load`, mapping into `TierConfig`.
Store any extra YAML fields (like `allowed_scale_degrees`) inside `TierConfig` by extending the dataclass to include them (minimal necessary to support later modules).

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_config_loader.py`

Expected: PASS.

---

### Task 3: Template library (`src/template_library.py`)

**Files:**
- Create: `melody-generator/src/template_library.py`
- Test: `melody-generator/tests/test_template_library.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_template_library.py`:

```python
from src.template_library import get_templates_for_tier


def test_templates_exist_for_each_tier():
    assert len(get_templates_for_tier(1)) >= 5
    assert len(get_templates_for_tier(2)) >= 5
    assert len(get_templates_for_tier(3)) >= 5
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_template_library.py`

Expected: FAIL (missing function/module).

- [ ] **Step 3: Implement minimal templates**

Implement ~5–10 templates per tier as dicts (id, bar_count options, cadence degrees, skeleton, etc.) and `get_templates_for_tier(tier: int) -> list[dict]`.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_template_library.py`

Expected: PASS.

---

### Task 4: Contour engine (`src/contour_engine.py`)

**Files:**
- Create: `melody-generator/src/contour_engine.py`
- Test: `melody-generator/tests/test_contour_engine.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_contour_engine.py`:

```python
from src.contour_engine import get_contour_curve


def test_contour_curve_shape_and_range():
    curve = get_contour_curve("arch", 10)
    assert len(curve) == 10
    assert all(0.0 <= x <= 1.0 for x in curve)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_contour_engine.py`

Expected: FAIL.

- [ ] **Step 3: Implement minimal contour curves**

Implement `arch`, `ascending`, `descending`, `wave`, `inverted-arch`, `plateau`, and `get_contour_curve(name, n)`.
Normalize outputs to [0,1] robustly.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_contour_engine.py`

Expected: PASS.

---

### Task 5: Rhythm generator (`src/rhythm_generator.py`) — meters without 6/8

**Files:**
- Create: `melody-generator/src/rhythm_generator.py`
- Test: `melody-generator/tests/test_rhythm_generator.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_rhythm_generator.py`:

```python
import random

from src.rhythm_generator import generate_rhythm, METER_BEATS_PER_BAR, DURATION_BEATS


def test_rhythm_sums_correctly_for_each_meter():
    rng = random.Random(1)
    for meter in ["4/4", "3/4", "2/4"]:
        for bars in [1, 2, 3, 4]:
            allowed = ["whole", "half", "quarter", "eighth"]
            rhythm = generate_rhythm(meter, bars, allowed, rng)
            total = sum(DURATION_BEATS[name] for name, _beats in rhythm)
            assert total == bars * METER_BEATS_PER_BAR[meter]


def test_generate_many_rhythms_never_overflows():
    rng = random.Random(2)
    for _ in range(200):
        meter = rng.choice(["4/4", "3/4", "2/4"])
        bars = rng.choice([1, 2, 3, 4])
        allowed = rng.choice(
            [["quarter", "eighth"], ["half", "quarter", "eighth"], ["whole", "half", "quarter", "eighth"]]
        )
        rhythm = generate_rhythm(meter, bars, allowed, rng)
        assert len(rhythm) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_rhythm_generator.py`

Expected: FAIL.

- [ ] **Step 3: Implement generator**

Implement:
- `DURATION_BEATS` mapping (whole=4, half=2, quarter=1, eighth=0.5)
- `METER_BEATS_PER_BAR` mapping for only 4/4,3/4,2/4
- `generate_rhythm(meter, bar_count, allowed_durations, rng)` using recursive or iterative fill that exactly matches beats per bar * bar_count; no rests.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_rhythm_generator.py`

Expected: PASS.

---

### Task 6: Cadence rules (`src/cadence_rules.py`)

**Files:**
- Create: `melody-generator/src/cadence_rules.py`
- Test: `melody-generator/tests/test_cadence_rules.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_cadence_rules.py`:

```python
from src.cadence_rules import get_cadence_degrees


def test_cadence_templates_return_degrees_or_none():
    degrees = get_cadence_degrees("authentic", rng_seed=1)
    assert degrees is not None
    assert all(isinstance(x, int) for x in degrees)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_cadence_rules.py`

Expected: FAIL.

- [ ] **Step 3: Implement minimal cadence lookup**

Implement a cadence template table (authentic/half/deceptive/plagal/open) and a selection function `get_cadence_degrees(cadence_type: str, rng_seed: int | None = None, rng=None)`.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_cadence_rules.py`

Expected: PASS.

---

### Task 7: Pitch generation (`src/pitch_generator.py`) — weighted sampling with constraints

**Files:**
- Create: `melody-generator/src/pitch_generator.py`
- Test: `melody-generator/tests/test_pitch_generator.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_pitch_generator.py`:

```python
import random

from src.pitch_generator import generate_pitch_sequence
from src.models import TierConfig


def _tier1_cfg() -> TierConfig:
    return TierConfig(
        name="Beginner",
        code="T1",
        keys=[{"tonic": "C", "mode": "major"}],
        bar_counts=[1, 2],
        meters=["4/4", "3/4", "2/4"],
        durations_normal=["quarter", "eighth"],
        durations_6_8=[],
        range_semitones_max=12,
        chromatic_allowed=False,
        chromatic_ratio_max=0.0,
        allowed_intervals_semitones=[1, 2, 3, 4, 5, 7],
        forbidden_intervals=[6, 10, 11],
        max_consecutive_leaps=1,
        leap_compensation_required=True,
        stepwise_ratio_min=0.70,
        start_scale_degrees=[1, 3, 5],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch", "ascending", "descending"],
        leading_tone_resolution_required=True,
    )


def test_pitch_sequence_stays_in_global_range_and_is_mostly_stepwise():
    rng = random.Random(1)
    cfg = _tier1_cfg()
    rhythm_durations = ["quarter"] * 16
    contour = [0.5] * len(rhythm_durations)
    pitches = generate_pitch_sequence(
        key_tonic="C",
        key_mode="major",
        contour_targets=contour,
        rhythm_durations=rhythm_durations,
        tier_config=cfg,
        rng=rng,
        starting_pitch=60,  # C4
    )
    assert len(pitches) == 16
    assert all(57 <= p <= 81 for p in pitches)
    intervals = [abs(pitches[i + 1] - pitches[i]) for i in range(len(pitches) - 1)]
    stepwise = sum(1 for x in intervals if x in (1, 2))
    assert stepwise / len(intervals) >= 0.60
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_pitch_generator.py`

Expected: FAIL.

- [ ] **Step 3: Implement minimal pitch generation**

Implement:
- global range constants `MIN_MIDI=57`, `MAX_MIDI=81`
- build candidate pitches from the current key/mode scale (music21 scale helpers ok, but keep it fast)
- apply hard filters: global range, tier interval rules, chromatic ratio limit, range max, consecutive leaps, (later) leading tone resolution
- weighted sampling using: distance to contour target, interval weight table, (optional) key profile weights (from `key_profiles.yaml` or internal constants)
- `generate_pitch_sequence(...) -> list[int]`

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_pitch_generator.py`

Expected: PASS.

---

### Task 8: Validator (`src/validator.py`) — hard constraint checking

**Files:**
- Create: `melody-generator/src/validator.py`
- Test: `melody-generator/tests/test_validator.py`

- [ ] **Step 1: Write failing tests (pass and fail cases)**

`melody-generator/tests/test_validator.py`:

```python
import random

from src.models import Melody, Note, TierConfig
from src.validator import validate_melody


def _cfg() -> TierConfig:
    return TierConfig(
        name="Beginner",
        code="T1",
        keys=[{"tonic": "C", "mode": "major"}],
        bar_counts=[1],
        meters=["4/4"],
        durations_normal=["quarter"],
        durations_6_8=[],
        range_semitones_max=12,
        chromatic_allowed=False,
        chromatic_ratio_max=0.0,
        allowed_intervals_semitones=[1, 2],
        forbidden_intervals=[],
        max_consecutive_leaps=1,
        leap_compensation_required=False,
        stepwise_ratio_min=0.5,
        start_scale_degrees=[1],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch"],
        leading_tone_resolution_required=False,
    )


def test_validator_rejects_out_of_range_pitch():
    cfg = _cfg()
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=56, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=60, duration="quarter", beat_position=1.0, bar_number=1),
        ],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    passed, violations = validate_melody(m, cfg)
    assert passed is False
    assert any("range" in v.lower() for v in violations)


def test_validator_accepts_simple_valid_melody():
    cfg = _cfg()
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
        ],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    passed, violations = validate_melody(m, cfg)
    assert passed is True
    assert violations == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
- `python -m pytest -q tests/test_validator.py`

Expected: FAIL.

- [ ] **Step 3: Implement validator**

Implement `validate_melody(melody: Melody, tier_config: TierConfig) -> tuple[bool, list[str]]` and check at least:
- all pitches within 57..81
- interval legality vs allowed/forbidden
- stepwise ratio threshold
- consecutive leap limit
- range semitones max
- start/end scale degree allowed (use music21 scale degrees based on key_tonic/key_mode)
- (later tasks can extend for chromatic ratio and leading-tone resolution once pitch generation supports it)

- [ ] **Step 4: Run tests to verify they pass**

Run:
- `python -m pytest -q tests/test_validator.py`

Expected: PASS.

---

### Task 9: Diversity checker (`src/diversity_checker.py`)

**Files:**
- Create: `melody-generator/src/diversity_checker.py`
- Test: `melody-generator/tests/test_diversity_checker.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_diversity_checker.py`:

```python
from src.diversity_checker import DiversityChecker
from src.models import Melody, Note


def _melody(pitches: list[int], durations: list[str]) -> Melody:
    notes = [
        Note(midi_pitch=p, duration=d, beat_position=float(i), bar_number=1)
        for i, (p, d) in enumerate(zip(pitches, durations))
    ]
    return Melody(
        melody_id="x",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )


def test_exact_duplicate_is_rejected():
    dc = DiversityChecker(max_similarity_threshold=0.2)
    m1 = _melody([60, 62, 64, 65], ["quarter"] * 4)
    m2 = _melody([60, 62, 64, 65], ["quarter"] * 4)
    assert dc.is_too_similar(m1) is False
    dc.register(m1)
    assert dc.is_too_similar(m2) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_diversity_checker.py`

Expected: FAIL.

- [ ] **Step 3: Implement diversity checker**

Implement interval-normalization, hash, parsons code, and Levenshtein threshold check as described in the source spec.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_diversity_checker.py`

Expected: PASS.

---

### Task 10: Difficulty scoring (`src/difficulty_scorer.py`)

**Files:**
- Create: `melody-generator/src/difficulty_scorer.py`
- Test: `melody-generator/tests/test_difficulty_scorer.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_difficulty_scorer.py`:

```python
from src.difficulty_scorer import score_melody
from src.models import Melody, Note


def test_difficulty_score_is_numeric_and_stable():
    notes = [
        Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
        Note(midi_pitch=64, duration="quarter", beat_position=2.0, bar_number=1),
        Note(midi_pitch=65, duration="quarter", beat_position=3.0, bar_number=1),
    ]
    m = Melody(
        melody_id="x",
        notes=notes,
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    composite, subs = score_melody(m)
    assert isinstance(composite, float)
    assert "interval_difficulty" in subs
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_difficulty_scorer.py`

Expected: FAIL.

- [ ] **Step 3: Implement scoring function**

Implement the formula from the source spec with interval weight mapping, returning `(composite_score: float, sub_scores: dict[str, float])`.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_difficulty_scorer.py`

Expected: PASS.

---

### Task 11: Metadata extraction (`src/metadata_extractor.py`)

**Files:**
- Create: `melody-generator/src/metadata_extractor.py`
- Test: `melody-generator/tests/test_metadata_extractor.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_metadata_extractor.py`:

```python
from src.metadata_extractor import build_metadata
from src.models import Melody, Note


def test_metadata_contains_required_top_level_fields():
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
        notes=[Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1)],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=42,
        template_id="T1_template",
    )
    md = build_metadata(m, version="1.0.0")
    assert md["id"] == "T1_Cmaj_44_1bar_arch_0001"
    assert "tonal" in md and "melodic" in md and "rhythmic" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_metadata_extractor.py`

Expected: FAIL.

- [ ] **Step 3: Implement metadata builder**

Implement `build_metadata(melody: Melody, version: str) -> dict` matching the required schema in the source spec (with fields populated from known generation parameters + computed interval/duration histograms).

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_metadata_extractor.py`

Expected: PASS.

---

### Task 12: MIDI exporter (`src/midi_exporter.py`)

**Files:**
- Create: `melody-generator/src/midi_exporter.py`
- Test: `melody-generator/tests/test_midi_exporter.py`

- [ ] **Step 1: Write failing test**

`melody-generator/tests/test_midi_exporter.py`:

```python
from pathlib import Path

import pretty_midi

from src.midi_exporter import export_midi
from src.models import Melody, Note


def test_export_midi_writes_readable_file(tmp_path: Path):
    m = Melody(
        melody_id="x",
        notes=[
            Note(midi_pitch=60, duration="quarter", beat_position=0.0, bar_number=1),
            Note(midi_pitch=62, duration="quarter", beat_position=1.0, bar_number=1),
        ],
        tier=1,
        key_tonic="C",
        key_mode="major",
        meter="4/4",
        bar_count=1,
        contour_type="arch",
        cadence_type="authentic",
        seed=1,
        template_id="t",
    )
    out = tmp_path / "x.mid"
    export_midi(m, out, tempo_bpm=90)
    pm = pretty_midi.PrettyMIDI(str(out))
    assert len(pm.instruments) == 1
    assert len(pm.instruments[0].notes) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_midi_exporter.py`

Expected: FAIL.

- [ ] **Step 3: Implement exporter**

Implement `export_midi(melody: Melody, filepath: str|Path, tempo_bpm: int = 90)` using `pretty_midi` and `DURATION_BEATS` conversion, ensuring no overlaps.

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_midi_exporter.py`

Expected: PASS.

---

### Task 13: Orchestrator (`src/melody_generator.py`) — generate one melody

**Files:**
- Create: `melody-generator/src/melody_generator.py`
- Test: `melody-generator/tests/test_end_to_end.py`

- [ ] **Step 1: Write failing integration test**

`melody-generator/tests/test_end_to_end.py`:

```python
import random

from src.config_loader import load_tier_config
from src.diversity_checker import DiversityChecker
from src.melody_generator import generate_one_melody
from src.template_library import get_templates_for_tier


def test_generate_one_melody_produces_valid_non_duplicate(tmp_path):
    cfg = load_tier_config("config/tier1.yaml")
    templates = get_templates_for_tier(1)
    rng = random.Random(123)
    dc = DiversityChecker(max_similarity_threshold=0.2)
    m = generate_one_melody(cfg, templates[0], batch_seed=20260414, sequence_num=1, diversity_checker=dc, rng=rng)
    assert m is not None
    assert len(m.notes) > 0
    assert all(57 <= n.midi_pitch <= 81 for n in m.notes)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_end_to_end.py`

Expected: FAIL.

- [ ] **Step 3: Implement minimal generate-one**

Implement `generate_one_melody(...)`:
- choose key/meter/bar_count/contour/cadence from cfg/template using seeded RNGs
- generate rhythm (`rhythm_generator`)
- generate pitches (`pitch_generator`)
- build `Melody` + `Note` objects with beat positions and bar numbers
- validate (`validator`)
- check similarity (`diversity_checker`)
- return melody or `None` after max attempts

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_end_to_end.py`

Expected: PASS.

---

### Task 14: Batch CLI (`scripts/generate_batch.py`) — generate N melodies + write files

**Files:**
- Create: `melody-generator/scripts/generate_batch.py`
- Create: `melody-generator/config/batch_config.yaml`
- Test: extend `melody-generator/tests/test_end_to_end.py` (batch smoke)

- [ ] **Step 1: Write failing test for batch generation**

Add to `tests/test_end_to_end.py`:

```python
from pathlib import Path
import json
import subprocess
import sys


def test_generate_batch_cli_smoke(tmp_path: Path):
    out_dir = tmp_path / "out"
    cfg_path = tmp_path / "batch.yaml"
    cfg_path.write_text(
        f'''
batch_id: "batch_test"
master_seed: 20260414
total_melodies: 6
tier_distribution:
  tier1: 2
  tier2: 2
  tier3: 2
meter_weights:
  "4/4": 0.50
  "3/4": 0.30
  "2/4": 0.20
output_directory: "{out_dir.as_posix()}"
quality_controls:
  max_generation_attempts: 10
  max_similarity_threshold: 0.20
''',
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "scripts/generate_batch.py", "--config", str(cfg_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    manifest = out_dir / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["batch_id"] == "batch_test"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
- `python -m pytest -q tests/test_end_to_end.py::test_generate_batch_cli_smoke`

Expected: FAIL.

- [ ] **Step 3: Implement CLI**

Implement:
- parse args
- load tier configs
- allocate quotas per tier and meter (simple weighted sampling acceptable v1)
- generate melodies and write:
  - `.mid` via `midi_exporter.export_midi`
  - `.json` via `metadata_extractor.build_metadata`
- write `manifest.json` with counts and basic stats

- [ ] **Step 4: Run test to verify it passes**

Run:
- `python -m pytest -q tests/test_end_to_end.py::test_generate_batch_cli_smoke`

Expected: PASS.

---

### Task 15: Verification + publish to GitHub

**Files:**
- Modify: `melody-generator/README.md` (setup + usage)
- New: GitHub repo (created/pushed)

- [ ] **Step 1: Full verification**

Run (from `melody-generator/`):
- `python -m pytest -q`

Expected: PASS.

- [ ] **Step 2: Generate small local batch for manual listening**

Run:
- `python scripts/generate_batch.py --config config/batch_config.yaml`

Expected: creates `output/batch_001/` with a small test size (keep `total_melodies` small for the first pass).

- [ ] **Step 3: Initialize git + push**

Commands (from workspace root or project folder as appropriate):
- initialize git
- create GitHub repo
- push default branch

Note: generated `output/` remains gitignored unless we explicitly decide to include a batch.

---

## Execution handoff
Plan saved to `docs/superpowers/plans/2026-04-14-monophonic-melody-generator.md`.

Two execution options:
1. **Subagent-Driven (recommended)** — dispatch per task and review between tasks
2. **Inline Execution** — implement tasks in this session with checkpoints

