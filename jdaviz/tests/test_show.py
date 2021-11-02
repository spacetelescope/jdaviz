import pytest
from jdaviz.app import Specviz

HAS_SIDECAR = False
try:
    import sidecar
    HAS_SIDECAR = True
except ImportError:
    pass  # HAS_SIDECAR = False


def test_show_inline():
    specviz = Specviz()
    res = specviz.show_inline()

    assert res is None


pytest.skipif('not HAS_SIDECAR')
def test_show_sidecar():
    specviz = Specviz()
    res = specviz.show_in_sidecar()
    assert isinstance(res, sidecar.Sidecar)


pytest.skipif('not HAS_SIDECAR')
def test_show_sidecar():
    specviz = Specviz()
    res = specviz.show_in_new_tab()
    assert isinstance(res, sidecar.Sidecar)