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

