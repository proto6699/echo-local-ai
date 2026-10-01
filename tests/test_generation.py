from neco.generation import pick_tier


def test_tier_boundaries() -> None:
    assert pick_tier(0.0) == "strange"
    assert pick_tier(0.02) == "unsettling"
    assert pick_tier(0.05) == "existential"
    assert pick_tier(0.10) == "fragment"
    assert pick_tier(0.50) == "mundane"
