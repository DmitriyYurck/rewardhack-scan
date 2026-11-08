from pricing import *  # noqa: F401,F403

def test_price_half():
    assert price_total([50, 50], 0.5) == 50.0
