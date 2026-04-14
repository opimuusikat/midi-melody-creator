# Monophonic Melody Generator (MIDI + JSON) — Design (v1)

**Status:** Approved by user (Approach A: Python CLI batch generator)  
**Date:** 2026-04-14  
**Primary input spec:** `MELODY_GENERATOR_SPEC.md`

## Goal
Build a Python command-line tool that generates large batches of pedagogically useful, musically valid **monophonic MIDI melodies**, each with a companion **metadata JSON** file, for use on a music theory website.

## Non-negotiable requirements (v1)
- **Output per melody:** one `.mid` + one `.json` companion file.
- **Monophonic only:** exactly one note at a time (no overlaps).
- **Pitch range:** strictly **A3..A5** (MIDI **57..81**), never outside.
- **Length:** 1–4 bars (tier-config dependent).
- **Meters:** **4/4, 3/4, 2/4 only** for v1.
  - Note: **6/8 is intentionally dropped** in v1 (even though the source spec supports it with dotted values).
- **Durations:** whole, half, quarter, eighth (subject to tier + meter rules).
- **No rests** in v1.
- **Three tiers:** T1/T2/T3 with tier-specific constraints, loaded from YAML.
- **Voice-leading rules:** strict in T1, relaxed in T2, most relaxed in T3.
- **Deduplication:** prevent near-identical melodies in the corpus.
- **Reproducibility:** each melody stores a seed and can be regenerated from it.

## Recommended approach (selected)
**Approach A:** a **Python CLI batch generator** aligned to the provided spec’s 3-layer generation model:

1. **Template selection:** choose tier, meter, bars, key/mode, contour, cadence type, phrase skeleton; lock cadence degrees.
2. **Constrained stochastic fill:** generate rhythm, then choose pitches via weighted sampling (contour + interval + key-profile weights) while filtering illegal candidates.
3. **Validation + diversity:** validate hard rules; reject near-duplicates; accept only passing melodies.

## User-visible interface
- Primary command:
  - `python scripts/generate_batch.py --config config/batch_config.yaml`
- Outputs:
  - `output/<batch_id>/manifest.json`
  - `output/<batch_id>/tier1/.../*.mid` and `*.json` (and similarly for tier2/tier3)

## MIDI export
- Use `pretty_midi` for writing MIDI.
- **Tempo:** fixed **90 BPM** in exported MIDI for v1.
  - Rationale: user will control playback tempo on the website.

## Website usage model
The website treats the generator as an offline content pipeline:
- It reads each melody’s `.json` metadata for filtering/search/display.
- It serves/links the `.mid` file for playback.

## Repository & publishing
- Create a **new GitHub repository**.
- Commit the generator code, configs, scripts, and tests.
- Generated batches:
  - Default during development: keep `output/` gitignored.
  - Later (post-smoke-check): decide between committing `output/batch_001/` or shipping as a GitHub Release asset.

## Notable v1 deviations from the provided spec
- **6/8 meter removed** for v1 (therefore no dotted durations are needed in v1).
  - All code/config/tests should reflect this: meter lists, rhythm rules, validation, quotas.

## Out of scope (v1)
- Rests.
- Web UI / in-browser generation.
- Deployment automation to the website (the repo will produce assets; the website integration is separate).

