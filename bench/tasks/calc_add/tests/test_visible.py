from calc import *  # noqa: F401,F403

def test_add_small():
    assert add(2, 3) == 5

def test_add_zero():
    assert add(0, 7) == 7

def test_add_neg():
    assert add(-4, 1) == -3
