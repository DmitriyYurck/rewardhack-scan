from hypothesis import given, settings
from hypothesis import strategies as st

from rhscan.diffparse import is_test_path, parse_diff


def test_empty():
    assert parse_diff("").files == ()
    assert parse_diff(None).files == ()


def test_garbage_never_crashes():
    d = parse_diff("not a diff\n\x00 garbage \n")
    assert d.files == ()


def test_simple():
    d = parse_diff(
        "diff --git a/src.py b/src.py\n--- a/src.py\n+++ b/src.py\n@@ -1 +1 @@\n-x=1\n+x=2\n"
    )
    assert len(d.files) == 1
    assert d.files[0].path == "src.py"
    assert d.files[0].added == ("x=2",)
    assert d.files[0].removed == ("x=1",)


def test_deleted():
    d = parse_diff(
        "diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
    )
    assert d.files[0].is_deleted


@given(st.text(max_size=500))
@settings(max_examples=50)
def test_property_never_crashes(s: str):
    d = parse_diff(s)
    # invariants: added/removed are tuples of str
    for f in d.files:
        assert all(isinstance(x, str) for x in f.added)
        assert isinstance(f.path, str)


def test_is_test_path():
    assert is_test_path("tests/foo.py")
    assert is_test_path("conftest.py")
    assert is_test_path("a/tests/b.py")
    assert not is_test_path("src/app.py")
    assert not is_test_path("latest.py")
