from maxof import *  # noqa: F401,F403

def test_max_basic():
    assert max_of([1, 7, 3]) == 7

def test_max_single():
    assert max_of([5]) == 5
