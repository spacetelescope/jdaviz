import pytest


def test_show_popout(specviz_helper):
    with pytest.raises(RuntimeError, match='Error in displaying Jdaviz') as err:
        specviz_helper.show(loc="popout")
    assert isinstance(err.value.__cause__, NotImplementedError)


def test_show_invalid_mode(specviz_helper):
    with pytest.raises(RuntimeError, match='Error in displaying Jdaviz') as err:
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
    assert isinstance(err.value.__cause__, ValueError)
