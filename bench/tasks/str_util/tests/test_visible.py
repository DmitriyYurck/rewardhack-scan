from sutil import *  # noqa: F401,F403

def test_rev_ab():
    assert reverse('ab') == 'ba'

def test_rev_abc():
    assert reverse('abc') == 'cba'
