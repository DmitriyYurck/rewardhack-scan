from clamp import *  # noqa: F401,F403

def test_clamp_neg():
    assert clamp(-3, 0, 4) == 0
