from clamp import *  # noqa: F401,F403

def test_clamp_lo():
    assert clamp(0, 1, 10) == 1

def test_clamp_hi():
    assert clamp(99, 1, 10) == 10

def test_clamp_mid():
    assert clamp(5, 1, 10) == 5
