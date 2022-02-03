import sidecar


def test_show_inline(specviz_helper):
    res = specviz_helper.show_inline()

    assert res is None


def test_show_sidecar(specviz_helper):
    res = specviz_helper.show_in_sidecar()
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_tab(specviz_helper):
    res = specviz_helper.show_in_new_tab()
    assert isinstance(res, sidecar.Sidecar)
