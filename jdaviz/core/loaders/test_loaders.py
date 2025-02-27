import pytest
from astropy import units as u
from specutils import SpectralRegion
from jdaviz.core.registries import loader_resolver_registry


def test_loaders_registry(specviz_helper):
    with pytest.raises(NotImplementedError):
        specviz_helper.loaders
    specviz_helper.app.state.dev_loaders = True
    # built-in loaders: file, url
    assert len(specviz_helper.loaders) == len(loader_resolver_registry.members)


def test_user_api(specviz_helper):
    specviz_helper.app.state.dev_loaders = True

    assert specviz_helper.app.state.drawer_content == 'plugins'

    loader = specviz_helper.loaders['file']
    loader.open_in_tray()
    assert specviz_helper.app.state.drawer_content == 'loaders'
    loader.close_in_tray()
    assert specviz_helper.app.state.drawer_content == 'loaders'
    loader.close_in_tray(close_sidebar=True)
    assert specviz_helper.app.state.drawer_content == ''

    subset_plg = specviz_helper.plugins['Subset Tools']
    subset_plg.open_in_tray()
    assert specviz_helper.app.state.drawer_content == 'plugins'

    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].open_in_tray()
    assert subset_plg._obj.loader_panel_ind == 0  # loader panel open
    subset_plg._obj.loaders['url'].close_in_tray()
    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].close_in_tray(close_sidebar=True)
    assert specviz_helper.app.state.drawer_content == ''


@pytest.mark.remote_data
def test_resolver_url(specviz_helper):
    specviz_helper.app.state.dev_loaders = True

    loader = specviz_helper.loaders['url']

    # no url, no valid formats
    assert len(loader.format.choices) == 0

    # non-valid input
    loader.url = 'not-valid-url'
    assert len(loader.format.choices) == 0

    loader.url = 'https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits'  # noqa
    assert len(loader.format.choices) == 2  # may change with future importers
    assert loader.format.selected == '2D Spectrum'

    # test target filtering
    assert len(loader.target.choices) > 1
    assert loader.target.selected == 'Any'
    loader.target = 'specviz-profile-viewer'
    assert len(loader.format.choices) == 1
    assert loader.format == '1D Spectrum List'
    assert loader.importer.data_label == '1D Spectrum'

    loader.target = 'Any'
    assert len(loader.format.choices) == 2
    loader.format = '2D Spectrum'
    assert loader.importer.data_label == '2D Spectrum'

    assert len(specviz_helper.app.data_collection) == 0

    loader.importer()

    assert len(specviz_helper.app.data_collection) == 1


def test_invoke_from_plugin(specviz_helper, spectrum1d, tmp_path):
    s = SpectralRegion(5*u.um, 6*u.um)
    local_path = str(tmp_path / 'spectral_region.ecsv')
    s.write(local_path)

    specviz_helper.load_data(spectrum1d)

    specviz_helper.app.state.dev_loaders = True
    specviz_helper.plugins['Subset Tools']._obj.dev_loaders = True

    loader = specviz_helper.plugins['Subset Tools'].loaders['file']

    assert len(loader.format.choices) == 0
    loader.filepath = local_path
    assert len(loader.format.choices) > 0

    loader.importer()
