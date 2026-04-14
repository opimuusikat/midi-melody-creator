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


def test_transposed_duplicate_is_rejected_by_interval_fingerprint():
    dc = DiversityChecker(max_similarity_threshold=0.2)
    m1 = _melody([60, 62, 64, 65], ["quarter"] * 4)
    m2 = _melody([65, 67, 69, 70], ["quarter"] * 4)  # same intervals +2 +2 +1
    dc.register(m1)
    assert dc.is_too_similar(m2) is True


def test_dedupe_state_persists_across_serialize_roundtrip():
    dc1 = DiversityChecker(max_similarity_threshold=0.2)
    m1 = _melody([60, 62, 64, 65], ["quarter"] * 4)
    dc1.register(m1)

    data = dc1.to_dict()
    dc2 = DiversityChecker.from_dict(data)

    m1_again = _melody([60, 62, 64, 65], ["quarter"] * 4)
    assert dc2.is_too_similar(m1_again) is True

    m1_transposed = _melody([65, 67, 69, 70], ["quarter"] * 4)
    assert dc2.is_too_similar(m1_transposed) is True


def test_to_dict_is_deterministic_even_with_different_insertion_orders():
    dc_a = DiversityChecker(max_similarity_threshold=0.2)
    dc_b = DiversityChecker(max_similarity_threshold=0.2)

    # Two different fingerprints (different rhythms) to produce two dict keys.
    m1 = _melody([60, 62, 64, 65], ["quarter"] * 4)
    m2 = _melody([60, 62, 64, 65], ["eighth"] * 4)

    dc_a.register(m1)
    dc_a.register(m2)

    dc_b.register(m2)
    dc_b.register(m1)

    assert dc_a.to_dict() == dc_a.to_dict()
    assert dc_a.to_dict() == dc_b.to_dict()


def test_generate_batch_loader_accepts_legacy_single_tier_state(tmp_path):
    from scripts.generate_batch import _load_dedupe_state_by_tier

    legacy = {
        "version": 1,
        "max_similarity_threshold": 0.99,  # should be overridden by loader
        "seen_hashes": ["h2", "h1"],
        "seen_parsons_rhythm": [
            {"parsons": "UR", "rhythm": ["quarter", "quarter", "quarter"], "candidates": [[1, 2]]}
        ],
    }
    p = tmp_path / "dedupe_state.json"
    p.write_text(__import__("json").dumps(legacy), encoding="utf-8")

    dc_by_tier = _load_dedupe_state_by_tier(p, max_sim=0.2)
    assert set(dc_by_tier.keys()) == {1, 2, 3}
    assert dc_by_tier[1].seen_hashes == {"h1", "h2"}
    assert dc_by_tier[1].max_similarity_threshold == 0.2
    assert dc_by_tier[2].max_similarity_threshold == 0.2
    assert dc_by_tier[3].max_similarity_threshold == 0.2

