from slug import *  # noqa: F401,F403

def test_slug_multi():
    assert slugify('  A  B  ') == 'a-b'
