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

