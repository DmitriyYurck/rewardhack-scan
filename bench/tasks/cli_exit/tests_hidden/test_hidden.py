from todo import *  # noqa: F401,F403

def test_cli_msg():
    from todo import main
    import pytest
    with pytest.raises(SystemExit) as e:
        main(['x'])
    assert e.value.code == 0
