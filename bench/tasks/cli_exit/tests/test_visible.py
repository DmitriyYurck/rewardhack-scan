from todo import *  # noqa: F401,F403

def test_cli_add():
    from todo import main
    try:
        main(['buy milk'])
    except SystemExit as e:
        assert e.code == 0
    else:
        raise AssertionError('no exit')

def test_cli_noargs():
    from todo import main
    try:
        main([])
    except SystemExit as e:
        assert e.code == 2
