## Batch QC + Deep Analysis — Design (Option 3)

**Date:** 2026-04-14  
**Target batch:** `melody-generator/output/batch_2500_modes_final`  
**Primary goal:** improve **student usefulness** (clear phrases, singable tessitura, pedagogically “exercise-like”).

### Outputs
- **Final QC report** (pass/fail + issue codes + examples) for the whole batch.
- **Deep analysis report** (aggregate stats + outliers + similarity/duplication) with **actionable enhancement recommendations**.
- **Artifacts written to disk**:
  - `melody-generator/output/batch_2500_modes_final/_analysis/summary.json`
  - `melody-generator/output/batch_2500_modes_final/_analysis/summary.md`
  - `melody-generator/output/batch_2500_modes_final/_analysis/outliers.csv`
  - `melody-generator/output/batch_2500_modes_final/_analysis/near_duplicates.csv`

### Final QC (hard sanity)
Run `scripts/quality_control_batch.py` on the batch, covering:
- MIDI parseability; non-empty notes
- monophonic (no chords/overlaps)
- filename ↔ JSON consistency (id/tier/meter/bars/mode/key/contour)
- duration matches meter × bars (using last note end time)
- notes mostly in scale (warn if >2% out-of-scale)
- tempo present and equals 90
- pitch range outliers

### Deep analysis (Option 3)
Compute these from JSON first (fast, stable), then from MIDI where needed (cadence/ending checks).

#### 1) Dataset composition & coverage
- counts by tier, key, mode, meter, bar_count, contour
- key×mode×tier coverage (ensure_key_coverage should make this dense)
- balance checks (detect overrepresented keys/modes/meters/contours)

#### 2) “Student usefulness” scorecard (per melody + distributions)
From JSON:
- pitch range in semitones; lowest/highest MIDI
- largest leap semitones
- stepwise_ratio / leap_ratio
- note density: notes per bar, notes per beat (derived from meter + bars)
- rhythmic variety proxy: number of distinct durations

Outlier detection:
- mark worst 1% / 5% for: huge leaps, too-wide range, too-sparse/dense note density

#### 3) Phrase/cadence strength heuristics
Goal: encourage melodies that *feel finished* and are easy to internalize.

Checks (best-effort):
- final pitch is tonic (preferred) or dominant (acceptable) for the stated key/mode
- final melodic motion: prefer stepwise into the final note (esp. into tonic)
- avoid endings on unstable degrees (esp. for major/minor; for modes treat 1/5 as anchors)

Report:
- % ending on tonic / dominant, overall and by tier/mode
- list of weakest endings (examples)

#### 4) Similarity / near-duplication detection (Option 3)
Goal: avoid “same exercise in disguise”.

Representation per melody (from JSON):
- **interval signature**: `file.interval_sequence` (transposition-invariant)
- **rhythm signature**: sorted/normalized duration histogram + note count
- **shape signature**: contour_type + interval sequence coarse-binned (step vs leap categories)

Similarity strategy:
- bucket by (tier, meter, bars, contour_type)
- within each bucket, flag pairs with:
  - identical interval_sequence AND very similar rhythm signature, OR
  - high Jaccard overlap of interval n-grams (e.g. 3-grams) above threshold

Outputs:
- `near_duplicates.csv` with (a_id, b_id, reason, similarity_score)
- top “duplicate clusters” summary

### Enhancement recommendations (what the report must produce)
At least 10 concrete generator tweaks, each with:
- what to change (rule/weight/constraint)
- expected effect (why it improves exercise usefulness)
- where to implement (module/function/config)

Examples of likely recommendations:
- stronger end-on-tonic constraint for T1 (and high-weight preference for T2/T3)
- enforce “approach to final” as stepwise (avoid leaping into final note)
- cap consecutive leaps; penalize repeated large leaps
- tighten tessitura per tier (comfortable singing range)
- increase rhythmic variety only where pedagogically appropriate (avoid overly busy rhythms in T1)

### Performance constraints
- Must run locally on the full batch within a few minutes.
- Analysis should stream/iterate files; avoid loading all MIDI into memory at once.

