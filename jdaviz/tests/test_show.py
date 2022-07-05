import pytest


def test_show_popout(specviz_helper):
    with pytest.raises(RuntimeError, match='Error in displaying Jdaviz'):
        specviz_helper.show(loc="popout")


def test_show_invalid_mode(specviz_helper):
    with pytest.raises(RuntimeError, match='Error in displaying Jdaviz'):
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
