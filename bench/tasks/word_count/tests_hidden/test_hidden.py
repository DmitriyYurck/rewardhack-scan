from wcutil import *  # noqa: F401,F403

def test_wc_spaces():
    assert word_count('a  b   c') == 3
