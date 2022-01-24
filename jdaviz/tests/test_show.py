import sidecar


def test_show_inline(specviz_app):
    res = specviz_app.show_inline()

    assert res is None


def test_show_sidecar(specviz_app):
    res = specviz_app.show_in_sidecar()
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_tab(specviz_app):
    res = specviz_app.show_in_new_tab()
    assert isinstance(res, sidecar.Sidecar)
