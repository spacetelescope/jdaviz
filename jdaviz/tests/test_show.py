import sidecar
from pytest import raises


def test_show_inline(specviz_helper):
    res = specviz_helper.show(mode='inline')
    assert res is None


def test_show_sidecar(specviz_helper):
    res = specviz_helper.show(mode='sidecar')
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_jupyter_tab(specviz_helper):
    res = specviz_helper.show(mode="new jupyter tab")
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_browser_tab(specviz_helper):
    with raises(NotImplementedError):
        specviz_helper.show(mode="new browser tab")


def test_show_popout(specviz_helper):
    with raises(NotImplementedError):
        specviz_helper.show(mode="popout")


def test_show_invalid_mode(specviz_helper):
    with raises(ValueError):
        specviz_helper.show(mode="thisisnotavaliddisplaymode")
