from dmerge import *  # noqa: F401,F403

def test_merge_override():
    assert merge_dict({'x': 1}, {'x': 9}) == {'x': 9}
