import sidecar
from pytest import warns


def test_show_inline(specviz_helper):
    res = specviz_helper.show(loc='inline')
    assert res is None


def test_show_sidecar(specviz_helper):
    res = specviz_helper.show(loc='sidecar')
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_browser_tab(specviz_helper):
    with warns(RuntimeWarning, match='Error detected in display'):
        specviz_helper.show(loc="new browser tab")


def test_show_popout(specviz_helper):
    with warns(RuntimeWarning):
        specviz_helper.show(loc="popout")


def test_show_invalid_mode(specviz_helper):
    with warns(RuntimeWarning):
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
