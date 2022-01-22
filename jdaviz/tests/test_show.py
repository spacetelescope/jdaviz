from jdaviz import Specviz
import sidecar


def test_show_inline():
    specviz = Specviz()
    res = specviz.show_inline()

    assert res is None


def test_show_sidecar():
    specviz = Specviz()
    res = specviz.show_in_sidecar()
    assert isinstance(res, sidecar.Sidecar)


def test_show_new_tab():
    specviz = Specviz()
    res = specviz.show_in_new_tab()
    assert isinstance(res, sidecar.Sidecar)
