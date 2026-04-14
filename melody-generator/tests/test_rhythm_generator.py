import random

from src.rhythm_generator import DURATION_BEATS, METER_BEATS_PER_BAR, generate_rhythm


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

