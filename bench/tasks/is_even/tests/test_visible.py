from evencheck import *  # noqa: F401,F403

def test_even_yes():
    assert is_even(4) is True

def test_even_no():
    assert is_even(3) is False
