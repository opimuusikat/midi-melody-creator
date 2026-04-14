import random

from src.config_loader import load_tier_config
from src.diversity_checker import DiversityChecker
from src.melody_generator import generate_one_melody
from src.template_library import get_templates_for_tier


def test_generate_one_melody_can_force_key():
    cfg = load_tier_config("config/tier1.yaml")
    template = get_templates_for_tier(1)[0]
    dc = DiversityChecker(max_similarity_threshold=0.2)
    rng = random.Random(1)
    m = generate_one_melody(
        cfg,
        template,
        batch_seed=20260414,
        sequence_num=1,
        diversity_checker=dc,
        rng=rng,
        max_attempts=200,
        forced_key={"tonic": "D", "mode": "major"},
    )
    assert m is not None
    assert m.key_tonic == "D"
    assert m.key_mode == "major"

