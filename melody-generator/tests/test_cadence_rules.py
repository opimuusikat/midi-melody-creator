from src.cadence_rules import get_cadence_degrees


def test_cadence_templates_return_degrees_or_none():
    degrees = get_cadence_degrees("authentic", rng_seed=1)
    assert degrees is not None
    assert all(isinstance(x, int) for x in degrees)

