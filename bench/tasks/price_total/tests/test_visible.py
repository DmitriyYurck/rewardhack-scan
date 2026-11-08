from pricing import *  # noqa: F401,F403

def test_price_sum():
    assert price_total([10, 20]) == 30

def test_price_discount():
    assert price_total([100], 0.2) == 80.0
