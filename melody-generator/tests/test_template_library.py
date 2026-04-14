from src.template_library import get_templates_for_tier


def test_templates_exist_for_each_tier():
    assert len(get_templates_for_tier(1)) >= 5
    assert len(get_templates_for_tier(2)) >= 5
    assert len(get_templates_for_tier(3)) >= 5

