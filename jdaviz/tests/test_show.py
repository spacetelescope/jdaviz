import sidecar
import pytest


def test_show_new_browser_tab(specviz_helper):
    with pytest.warns(RuntimeWarning, match='Error detected in display'):
        specviz_helper.show(loc="new browser tab")


def test_show_popout(specviz_helper):
    with pytest.warns(RuntimeWarning):
        specviz_helper.show(loc="popout")


def test_show_invalid_mode(specviz_helper):
    with pytest.warns(RuntimeWarning):
        specviz_helper.show(loc="thisisnotavaliddisplaymode")
