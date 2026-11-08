from calc import *  # noqa: F401,F403

def test_add_large():
    assert add(100, 55) == 155

def test_add_float():
    assert add(1.5, 2.25) == 3.75
