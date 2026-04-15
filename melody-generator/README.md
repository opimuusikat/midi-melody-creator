# Melody Generator (Monophonic MIDI + JSON)

Python CLI tool to generate batches of **monophonic** MIDI melodies plus per-melody **metadata JSON** for use on a music theory website.

## Requirements
- Python 3.10+

## Setup

```bash
cd melody-generator
brew install python@3.11

# Note: this workspace path contains ":" which prevents creating a venv inside it.
# Create a venv outside the repo:
/opt/homebrew/bin/python3.11 -m venv "$HOME/.venvs/melody-generator"
"$HOME/.venvs/melody-generator/bin/python" -m pip install -r requirements.txt
```

## Run tests

```bash
"$HOME/.venvs/melody-generator/bin/python" -m pytest -q
```

## Generate a batch

```bash
"$HOME/.venvs/melody-generator/bin/python" scripts/generate_batch.py --config config/batch_config.yaml
```

## Analyze a MIDI corpus (reference transcriptions)

Aggregates features for arbitrary `.mid` directories (parallel workers). Outputs `records.jsonl`, `summary.json`, and `summary.md`.

```bash
"$HOME/.venvs/melody-generator/bin/python" scripts/analyze_midi_corpus.py --input-dir "../midi for analyiz" --out-dir "../midi for analyiz/_corpus_analysis" --workers 6
```

Corpus priors (empirical + theory pointers, **not** tier replacements): `config/melody_corpus_prior.yaml`. See repo root `AGENTS.md`.

Example **300-melody** corpus-informed batch + QC/deep analysis + comparison to a default-tier batch and the MIDI corpus: `config/batch_300_corpus_priors.yaml`, then `scripts/compare_melody_summaries.py` (see `AGENTS.md`).

## Website integration (OpiMuusikat)

If you are generating dictations for the OpiMuusikat website, follow the strict output contract:
`docs/opi-dictation-integration-rulebook.md`.

