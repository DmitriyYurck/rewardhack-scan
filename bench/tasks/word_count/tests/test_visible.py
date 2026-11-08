from wcutil import *  # noqa: F401,F403

def test_wc_two():
    assert word_count('hello world') == 2

def test_wc_one():
    assert word_count('hello') == 1
