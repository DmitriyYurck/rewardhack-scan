from dd import *  # noqa: F401,F403

def test_dd_strings():
    assert dedupe(['b', 'a', 'b']) == ['b', 'a']
