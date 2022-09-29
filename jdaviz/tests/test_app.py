import pytest

from jdaviz import Application, Specviz
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


def test_nonstandard_specviz_viewer_name():
    config = {'settings': {'configuration': 'nonstandard',
                           'data': {'parser': 'specviz-spectrum1d-parser'},
                           'visible': {'menu_bar': False,
                                       'toolbar': True,
                                       'tray': True,
                                       'tab_headers': False},
                           'context': {'notebook': {'max_height': '750px'}}},
              'toolbar': ['g-data-tools', 'g-subset-tools'],
              'tray': ['g-metadata-viewer',
                       'g-plot-options',
                       'g-subset-plugin',
                       'g-gaussian-smooth',
                       'g-model-fitting',
                       'g-unit-conversion',
                       # 'g-line-list' and 'specviz-line-analysis' are not
                       # supported by the custom config adaptations for now
                       'g-export-plot'],
              'viewer_area': [{'container': 'col',
                               'children': [{'container': 'row',
                                             'viewers': [{'name': 'H',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'h'},
                                                         {'name': 'K',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'k'}]}]}]}

    class Customviz(Specviz):
        _default_configuration = config

    viz = Customviz()
    assert viz.app.get_viewer_reference_names() == ['h', 'k']
