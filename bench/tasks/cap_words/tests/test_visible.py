from cap import *  # noqa: F401,F403

def test_cap_basic():
    assert cap_words('hello world') == 'Hello World'

def test_cap_one():
    assert cap_words('hi') == 'Hi'
