# OpiMuusikat dictation integration — output rulebook (v1)

This document defines the **required output contract** for `midi-melody-creator` so that the
OpiMuusikat web app can ingest generated dictations without manual fixes.

It intentionally mirrors the website-side rulebook and audit logic:
- Website rulebook: `opi-muusikat-v2/docs/dictation-tier-rulebook.md`
- Website audit implementation: `opi-muusikat-v2/src/utils/dictationTierRules.ts`

## 1) Output pairs (required)

For each melody, output **two files** with the same basename in the same folder:

- `*.mid`
- `*.json`

The website copies these pairs under `public/dictations/**` and then rebuilds its index:
`npm run dictations:index`.

## 2) MIDI requirements (strict)

The website’s current bridge assumes:

- **Monophonic only**: no overlapping notes anywhere.
- **No rests / gaps** between consecutive notes (contiguous export).
- **No bar-crossing notes**: a single note must not cross a bar boundary.
- **Durations**: whole / half / quarter / eighth only.

If you want to introduce rests or other durations later, the website bridge must be upgraded first.

## 3) JSON metadata requirements (minimum schema)

The website must be able to parse at least these fields:

```json
{
  "id": "string",
  "tonal": { "key": "C|G|F|Bb|F#|...", "mode": "major|minor|..." },
  "rhythmic": { "meter": "2/4|3/4|4/4", "bar_count": 1 },
  "difficulty": { "tier": 1 }
}
```

### 3.1 `tonal.key` (required)

- Use conventional key names, e.g. `C`, `G`, `F`, `Bb`, `F#`, `Cb`.
- Do **not** output “C major”, lowercase keys, or locale-specific names.

### 3.2 `tonal.mode` (required)

- Must be **lowercase**.
- Allowed modes by tier (see tier rules below):
  - Tier 1: `major`, `minor`, `natural_minor`
  - Tier 2: + `harmonic_minor`, `melodic_minor`, `dorian`, `mixolydian`
  - Tier 3: + `phrygian`, `lydian`
- Unknown mode should be treated conservatively as **minimum tier 2** by the website audit.

### 3.3 `rhythmic.meter` (required)

For v1 website compatibility, restrict to:
- `2/4`, `3/4`, `4/4`

### 3.4 `rhythmic.bar_count` (required; hard cap)

Hard requirement:
- **1–4 bars** for all tiers

Website behavior:
- items outside 1–4 are rejected/capped out during indexing and loading.

### 3.5 `difficulty.tier` (required in practice)

Although the website can default a missing tier to 1, for production batches you should always output:
- `difficulty.tier` as an integer `1..3`

## 4) Tier rulebook (must match website audit)

The website enforces:

> `declared tier (difficulty.tier) >= content minimum tier`

If a melody is declared **easier** than its content requires, the website will **skip** it during
random selection.

Compute content minimum tier as:

> `minimumTier = clamp(1..3, max(modeMin, barCountMin, keyStrengthMin, chromaticMin))`

### 4.1 Mode minimum tier (`tonal.mode`)

- Tier 1 modes → min 1
- Tier 2 extra modes → min 2
- Tier 3 modes → min 3
- Unknown → min 2

### 4.2 Bar count minimum tier (`rhythmic.bar_count`)

- 1–2 bars → min 1
- 3–4 bars → min 2

### 4.3 Key strength minimum tier (parent major accidental count)

The website maps minor/modes to a “parent major” and counts accidentals (VexFlow-style).

- ≤2 accidentals → min 1
- 3–4 → min 2
- ≥5 → min 3

### 4.4 Chromaticism minimum tier (`tonal.*` preferred; fallback `melodic.*`)

The website uses either location (support both):
- `tonal.chromatic_ratio`, `tonal.chromatic_note_count`
- or `melodic.chromatic_ratio`, `melodic.chromatic_note_count`

Thresholds:
- min 1 if `ratio < 0.12` and `chromatic_note_count < 2`
- min 2 if `ratio >= 0.12` or `chromatic_note_count >= 2`
- min 3 if `ratio >= 0.28` or `chromatic_note_count >= 4`

If chromatic fields are missing, min chromatic tier defaults to **1**.

## 5) Optional but recommended fields

- `rhythmic.suggested_tempo_bpm`: number (website uses it to derive playback tempo; website parser accepts 20–300).
- `file.midi_filename`: for traceability when exporting batches.
- Any additional analysis fields are fine as long as required fields remain stable.

