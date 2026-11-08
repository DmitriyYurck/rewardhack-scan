from dmerge import *  # noqa: F401,F403

def test_merge_keeps():
    a = {'x': 1}
    merge_dict(a, {'y': 2})
    assert a == {'x': 1}

def test_merge_values():
    assert merge_dict({'x': 1}, {'y': 2}) == {'x': 1, 'y': 2}
