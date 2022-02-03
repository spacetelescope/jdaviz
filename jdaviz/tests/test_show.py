import sidecar


def test_show_inline(specviz_helper):
    res = specviz_helper.show(mode='inline')

    assert res is specviz_helper.app


def test_show_sidecar(specviz_helper):
    res = specviz_helper.show(mode='sidecar')
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_tab(specviz_helper):
    res = specviz_helper.show(mode="new jupyter tab")
    assert isinstance(res, sidecar.Sidecar)
