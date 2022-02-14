import pytest

from jdaviz import Application
from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth


# This applies to all viz but testing with Imviz should be enough.
def test_viewer_calling_app(imviz_helper):
    viewer = imviz_helper.default_viewer
    assert viewer.session.jdaviz_app is imviz_helper.app


def test_get_tray_item_from_name():
    app = Application(configuration='default')
    plg = app.get_tray_item_from_name('g-gaussian-smooth')
    assert isinstance(plg, GaussianSmooth)

    with pytest.raises(KeyError, match='not found in app'):
        app.get_tray_item_from_name('imviz-compass')
