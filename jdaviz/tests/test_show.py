import pytest


def test_show_popout(specviz_helper):
    try:
        specviz_helper.show(loc="popout")
    except RuntimeError as err:
        assert hasattr(err, '__cause__') and isinstance(err.__cause__, NotImplementedError)


def test_show_invalid_mode(specviz_helper):
    try:
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
    except RuntimeError as err:
        assert hasattr(err, '__cause__') and isinstance(err.__cause__, ValueError)
