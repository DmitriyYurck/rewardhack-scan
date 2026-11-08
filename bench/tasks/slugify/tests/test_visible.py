from slug import *  # noqa: F401,F403

def test_slug_basic():
    assert slugify('Hello World') == 'hello-world'

def test_slug_punct():
    assert slugify('C++ Rocks!') == 'c-rocks'
