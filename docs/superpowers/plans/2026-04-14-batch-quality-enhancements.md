# Batch Quality Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve student usefulness of generated melodies and make batch outputs complete and auditable (manifest + expected tier counts), while reducing “same exercise in disguise” across transpositions.

**Architecture:** Add a small set of **new validator constraints** (cadence approach, density cap) configurable per tier, and strengthen deduplication to be **explicitly transposition-invariant** using a stable fingerprint. Add a small batch “finalizer” script to ensure `manifest.json` and expected counts exist in the final output folder.

**Tech Stack:** Python 3, `pytest`, `music21`, existing generator modules in `melody-generator/src/`.

---

## File structure changes (what each file will do)

- **Modify** `melody-generator/src/models.py`
  - Add optional tier-config fields for new hard rules: note density cap and cadence approach requirement.
- **Modify** `melody-generator/src/config_loader.py`
  - No logic changes required if new TierConfig fields have defaults; loader already supports optional defaults.
- **Modify** `melody-generator/src/validator.py`
  - Enforce:
    - max notes per beat / per bar (tier-configurable)
    - “final approach stepwise into final note” for tiers that require it
- **Modify** `melody-generator/config/tier1.yaml` (and optionally tier2/tier3)
  - Turn on the new constraints where they help student usefulness (T1 strict; T2 softer).
- **Modify** `melody-generator/src/diversity_checker.py`
  - Add a more stable, explicit fingerprint and (optionally) persistable state to prevent transposed clones, even across multi-run merges.
- **Create** `melody-generator/scripts/finalize_batch.py`
  - Create/repair `manifest.json` in a “final” output directory and validate tier counts.
- **Create tests** under `melody-generator/tests/`
  - Unit tests for new validator behavior and dedupe fingerprint.

---

### Task 1: Add new TierConfig fields (density + cadence approach)

**Files:**
- Modify: `melody-generator/src/models.py`
- Modify: `melody-generator/config/tier1.yaml`
- Modify (optional): `melody-generator/config/tier2.yaml`
- Test: `melody-generator/tests/test_validator_student_usefulness.py`

- [ ] **Step 1: Write failing tests for new TierConfig defaults**

```python
# melody-generator/tests/test_validator_student_usefulness.py
from src.models import TierConfig

def test_tierconfig_has_defaults_for_new_fields():
    # If TierConfig adds fields, existing YAMLs must still load without specifying them.
    assert hasattr(TierConfig, "max_notes_per_beat")
    assert hasattr(TierConfig, "require_stepwise_final_approach")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
- `cd melody-generator && .venv/bin/python -m pytest -q tests/test_validator_student_usefulness.py::test_tierconfig_has_defaults_for_new_fields`

Expected: FAIL because fields don’t exist yet.

- [ ] **Step 3: Implement TierConfig defaults**

Update `TierConfig` to include:
- `max_notes_per_beat: float | None = None`
- `max_notes_per_bar: int | None = None`
- `require_stepwise_final_approach: bool = False`

- [ ] **Step 4: Re-run the test**

Expected: PASS.

- [ ] **Step 5: Update `tier1.yaml` to enable the new constraints**

Add (proposed initial values):
- `require_stepwise_final_approach: true`
- `max_notes_per_beat: 1.25`  (prevents “too busy” T1 exercises)

Keep T2/T3 off initially unless you want tighter constraints.

- [ ] **Step 6: Run existing tests**

Run: `cd melody-generator && .venv/bin/python -m pytest -q`

Expected: PASS.

---

### Task 2: Enforce “stepwise approach into final note” + density caps in validator

**Files:**
- Modify: `melody-generator/src/validator.py`
- Test: `melody-generator/tests/test_validator_student_usefulness.py`

- [ ] **Step 1: Write failing tests**

```python
# melody-generator/tests/test_validator_student_usefulness.py
from src.models import Melody, Note, TierConfig
from src.validator import validate_melody

def _mk_tier(**overrides):
    base = dict(
        name="Beginner", code="T1",
        keys=[{"tonic":"C","mode":"major"}],
        bar_counts=[1], meters=["4/4"],
        durations_normal=["quarter","eighth"], durations_6_8=[],
        range_semitones_max=12,
        allowed_scale_degrees=[1,2,3,4,5,6,7],
        chromatic_allowed=False, chromatic_ratio_max=0.0, modal_mixture_allowed=False,
        allowed_intervals_semitones=[1,2,3,4,5,7],
        forbidden_intervals=[6,10,11],
        max_consecutive_leaps=1,
        leap_compensation_required=True,
        stepwise_ratio_min=0.7,
        start_scale_degrees=[1,3,5],
        end_scale_degrees=[1],
        cadence_types=["authentic"],
        contour_types=["arch"],
        leading_tone_resolution_required=True,
        # new fields may be overridden below
    )
    base.update(overrides)
    return TierConfig(**base)

def test_validator_rejects_non_stepwise_final_approach_when_required():
    tier = _mk_tier(require_stepwise_final_approach=True)
    # Ends on tonic (C) but approaches by a leap (G->C is 5 semitones).
    notes = [
        Note(midi_pitch=67, duration="quarter", beat_position=0.0, bar_number=1),  # G4
        Note(midi_pitch=72, duration="quarter", beat_position=1.0, bar_number=1),  # C5
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0001",
        notes=notes, tier=1,
        key_tonic="C", key_mode="major",
        meter="4/4", bar_count=1,
        contour_type="arch", cadence_type="authentic",
        seed=1, template_id="t",
    )
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("final approach" in v.lower() for v in violations)

def test_validator_rejects_too_dense_when_max_notes_per_beat_set():
    tier = _mk_tier(max_notes_per_beat=1.0)
    # 4/4, 1 bar => 4 beats. 6 notes => 1.5 notes/beat (too dense).
    notes = [
        Note(midi_pitch=60, duration="eighth", beat_position=0.0, bar_number=1),
        Note(midi_pitch=62, duration="eighth", beat_position=0.5, bar_number=1),
        Note(midi_pitch=64, duration="eighth", beat_position=1.0, bar_number=1),
        Note(midi_pitch=65, duration="eighth", beat_position=1.5, bar_number=1),
        Note(midi_pitch=67, duration="eighth", beat_position=2.0, bar_number=1),
        Note(midi_pitch=60, duration="eighth", beat_position=2.5, bar_number=1),
    ]
    m = Melody(
        melody_id="T1_Cmaj_44_1bar_arch_0002",
        notes=notes, tier=1,
        key_tonic="C", key_mode="major",
        meter="4/4", bar_count=1,
        contour_type="arch", cadence_type="authentic",
        seed=1, template_id="t",
    )
    ok, violations = validate_melody(m, tier)
    assert ok is False
    assert any("density" in v.lower() or "notes per beat" in v.lower() for v in violations)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
- `cd melody-generator && .venv/bin/python -m pytest -q tests/test_validator_student_usefulness.py`

Expected: FAIL with missing violations.

- [ ] **Step 3: Implement validator logic**

In `validate_melody`:
- If `tier_config.require_stepwise_final_approach`:
  - compute final interval \( |p[-1]-p[-2]| \) and require it in `{1,2}`
- If `tier_config.max_notes_per_beat`:
  - compute total beats from `melody.meter` × `melody.bar_count`
  - compute notes_per_beat = len(notes)/total_beats
  - reject if above cap
- If `tier_config.max_notes_per_bar`:
  - reject if (len(notes)/bar_count) above cap

- [ ] **Step 4: Re-run tests**

Expected: PASS.

---

### Task 3: Strengthen deduplication to avoid “same exercise in disguise” across merges

**Files:**
- Modify: `melody-generator/src/diversity_checker.py`
- Create: `melody-generator/tests/test_diversity_checker_fingerprint.py`

- [ ] **Step 1: Add tests ensuring the fingerprint is transposition-invariant and stable**

```python
# melody-generator/tests/test_diversity_checker_fingerprint.py
from src.diversity_checker import DiversityChecker
from src.models import Melody, Note

def _melody(pitches, durations):
    notes=[]
    beat=0.0
    for p,d in zip(pitches,durations):
        notes.append(Note(midi_pitch=p, duration=d, beat_position=beat, bar_number=1))
        beat += 0.5 if d=="eighth" else 1.0
    return Melody(
        melody_id="X", notes=notes, tier=1,
        key_tonic="C", key_mode="major", meter="4/4", bar_count=1,
        contour_type="arch", cadence_type="authentic", seed=1, template_id="t"
    )

def test_transposed_clone_is_duplicate():
    dc = DiversityChecker(max_similarity_threshold=0.2)
    a = _melody([60,62,64,65], ["quarter","quarter","quarter","quarter"])
    b = _melody([65,67,69,70], ["quarter","quarter","quarter","quarter"])  # +5 transpose
    assert dc.is_too_similar(a) is False
    dc.register(a)
    assert dc.is_too_similar(b) is True
```

- [ ] **Step 2: Run and confirm behavior**

Run: `cd melody-generator && .venv/bin/python -m pytest -q tests/test_diversity_checker_fingerprint.py`

- [ ] **Step 3: Optional enhancement: persist dedupe state**

Add methods to `DiversityChecker`:
- `to_json()` / `from_json()`
- allow `scripts/generate_batch.py` to load/save a `dedupe_state.json` inside the output dir so re-runs don’t reintroduce duplicates when you merge batches.

---

### Task 4: Add a `finalize_batch.py` script to ensure completeness + manifest

**Files:**
- Create: `melody-generator/scripts/finalize_batch.py`
- Test: `melody-generator/tests/test_finalize_batch.py`

- [ ] **Step 1: Define desired behavior**
Script inputs:
- `--source-dir output/<some_batch>`
- `--final-dir output/batch_2500_modes_final`
- `--expected-tier1 1000 --expected-tier2 900 --expected-tier3 600` (optional)

Script actions:
- copy `*.mid` + `*.json` + `manifest.json` into final dir
- verify expected tier counts (by filename prefix `T1_`, `T2_`, `T3_`)
- exit non-zero if missing tiers or missing manifest

- [ ] **Step 2: Write tests using a temp directory**

Test should assert it fails when T3 is incomplete (matching what we observed in `batch_2500_modes_final`).

---

## Verification (must do at end)

- [ ] Run full test suite:
  - `cd melody-generator && .venv/bin/python -m pytest -q`
- [ ] Regenerate a small batch (e.g. 20 melodies) and run QC:
  - `cd melody-generator && .venv/bin/python scripts/generate_batch.py --config config/batch_2500_modes_v2.yaml`
  - `cd melody-generator && .venv/bin/python scripts/quality_control_batch.py --batch-dir output/batch_2500_modes_v3`

