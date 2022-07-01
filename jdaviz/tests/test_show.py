import sidecar
import pytest


def test_show_inline(specviz_helper):
    res = specviz_helper.show(loc='inline')
    assert res is None


def test_show_sidecar(specviz_helper):
    res = specviz_helper.show(loc='sidecar')
    assert isinstance(res, sidecar.Sidecar)


def test_known_sidecar_anchors(specviz_helper):
    anchors = ['split-right', 'split-left', 'split-top', 'split-bottom',
               'tab-before', 'tab-after', 'right']
    for anchor in anchors:
        res = specviz_helper.show(loc=f"sidecar:{anchor}")
        assert isinstance(res, sidecar.Sidecar)


def test_show_new_browser_tab(specviz_helper):
    with pytest.warns(RuntimeWarning, match='Error detected in display'):
        specviz_helper.show(loc="new browser tab")


def test_show_popout(specviz_helper):
    with pytest.warns(RuntimeWarning):
        specviz_helper.show(loc="popout")


def test_show_invalid_mode(specviz_helper):
    with pytest.warns(RuntimeWarning):
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
