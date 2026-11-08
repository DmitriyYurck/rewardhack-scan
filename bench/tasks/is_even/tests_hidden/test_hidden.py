from evencheck import *  # noqa: F401,F403

def test_even_big():
    assert is_even(1000) is True and is_even(999) is False
