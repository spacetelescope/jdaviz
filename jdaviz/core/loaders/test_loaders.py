import numpy as np
import pytest
from astropy import units as u
from specutils import SpectralRegion, Spectrum1D
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import find_matching_resolver


def test_loaders_registry(specviz_helper):
    # built-in loaders: file, url, etc
    assert len(specviz_helper.loaders) == len(loader_resolver_registry.members)


def test_open_close(specviz_helper):
    specviz_helper.app.state.dev_loaders = True

    assert specviz_helper.app.state.drawer_content == ''

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


def test_resolver_matching(specviz_helper):
    sp = Spectrum1D(spectral_axis=np.array([1, 2, 3])*u.nm,
                    flux=np.array([1, 2, 3])*u.Jy)

    res_sp = find_matching_resolver(specviz_helper.app, sp)
    assert res_sp._obj._registry_label == 'object'
    assert res_sp.format == '1D Spectrum'

    specviz_helper._load(sp)
    assert len(specviz_helper.app.data_collection) == 1


def test_trace_importer(specviz2d_helper, spectrum2d):
    specviz2d_helper._load(spectrum2d, format='2D Spectrum')

    trace = specviz2d_helper.plugins['Spectral Extraction'].export_trace()

    res_sp = find_matching_resolver(specviz2d_helper.app, trace)
    assert res_sp._obj._registry_label == 'object'
    assert res_sp.format == 'Trace'

    # import through loader API
    ldr = specviz2d_helper.loaders['object']
    ldr.object = trace
    assert ldr.format == 'Trace'
    ldr.importer.data_label = 'Trace 1'
    ldr.importer()
    assert specviz2d_helper.app.data_collection[-1].label == 'Trace 1'

    # import through load method
    specviz2d_helper._load(trace, data_label='Trace 2')
    assert specviz2d_helper.app.data_collection[-1].label == 'Trace 2'


def test_markers_specviz2d_unit_conversion(specviz2d_helper, spectrum2d):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum1D(flux=data*u.MJy, spectral_axis=data[3]*u.AA)
    specviz2d_helper.load_data(spectrum2d)


@pytest.mark.remote_data
def test_resolver_url(deconfigged_helper):
    loader = deconfigged_helper.loaders['url']

    # no url, no valid formats
    assert len(loader.format.choices) == 0

    # non-valid input
    loader.url = 'not-valid-url'
    assert len(loader.format.choices) == 0

    loader.url = 'https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits'  # noqa
    assert len(loader.format.choices) == 3  # may change with future importers
    assert loader.format.selected == '2D Spectrum'  # default may change with future importers

    # test target filtering
    assert len(loader.target.choices) > 1
    assert loader.target.selected == 'Any'
    loader.target = '1D Spectrum'
    assert len(loader.format.choices) == 2  # may change with future importers
    assert loader.format == '1D Spectrum List'  # default may change with future importers
    assert loader.importer.data_label == '1D Spectrum'

    loader.target = 'Any'
    assert len(loader.format.choices) == 3
    loader.format = '2D Spectrum'
    assert loader.importer.data_label == '2D Spectrum'

    assert len(deconfigged_helper.app.data_collection) == 0
    assert len(deconfigged_helper.viewers) == 0

    loader.importer()

    # 2D spectrum and auto-extracted 1D spectrum
    assert len(deconfigged_helper.app.data_collection) == 2
    assert len(deconfigged_helper.viewers) == 2


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
