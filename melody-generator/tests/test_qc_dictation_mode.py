"""Unit tests for scripts/quality_control_batch.py dictation-mode helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from music21 import note as m21note  # type: ignore


def _load_qc_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "quality_control_batch.py"
    name = "_quality_control_batch_for_tests"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Required so dataclasses can resolve string annotations when loading via importlib.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qc():
    return _load_qc_module()


def test_dictation_quarter_length_allowed(qc):
    assert qc._dictation_quarter_length_allowed(1.0)
    assert qc._dictation_quarter_length_allowed(0.5)
    assert not qc._dictation_quarter_length_allowed(1.5)
    assert not qc._dictation_quarter_length_allowed(3.0)


def test_resolve_meter_bars_from_parsed(qc):
    p = {"meter_num": "4", "meter_den": "4", "bars": "2"}
    assert qc._resolve_meter_bars_dictation(p, None) == (4, 4, 2)


def test_resolve_meter_bars_from_json(qc):
    md = {"rhythmic": {"meter": "3/4", "bar_count": 2}}
    assert qc._resolve_meter_bars_dictation(None, md) == (3, 4, 2)


def test_opi_dictation_bar_crossing_fail(qc):
    """One whole note across 2 bars of 2/4 must fail the no-bar-crossing rule."""
    n0 = m21note.Note()
    n0.offset = 0.0
    n0.quarterLength = 4.0
    parsed = {"meter_num": "2", "meter_den": "4", "bars": "2"}
    md = {
        "rhythmic": {"meter": "2/4", "bar_count": 2},
        "difficulty": {"tier": 1},
    }
    issues = qc._opi_dictation_rulebook_issues(notes=[n0], parsed=parsed, md=md)
    codes = {i.code for i in issues}
    assert "dictation.bar_crossing" in codes


def test_opi_dictation_clean_simple(qc):
    n0 = m21note.Note()
    n0.offset = 0.0
    n0.quarterLength = 2.0
    n1 = m21note.Note()
    n1.offset = 2.0
    n1.quarterLength = 2.0
    parsed = {"meter_num": "4", "meter_den": "4", "bars": "1"}
    md = {
        "rhythmic": {"meter": "4/4", "bar_count": 1},
        "difficulty": {"tier": 1},
    }
    issues = qc._opi_dictation_rulebook_issues(notes=[n0, n1], parsed=parsed, md=md)
    assert issues == []
