from dd import *  # noqa: F401,F403

def test_dd_order():
    assert dedupe([3, 1, 3, 2]) == [3, 1, 2]

def test_dd_empty():
    assert dedupe([]) == []
