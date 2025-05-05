import pytest
from regions import EllipsePixelRegion, PixCoord
from specutils import SpectralRegion

from jdaviz import Cubeviz
from jdaviz.app import Application
from jdaviz.core.config import get_configuration


def test_nested_helper(cubeviz_helper):
    '''Ensures the Cubeviz helper is always returned, even after the Specviz helper is called'''
    # Force Specviz helper to instantiate
    cubeviz_helper.specviz

    assert cubeviz_helper.app._jdaviz_helper == cubeviz_helper

    # The viewers also have a callthrough to the app's _jdaviz_helper attribute
    spec_viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')
    assert spec_viewer.jdaviz_helper == cubeviz_helper


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(cubeviz_helper):
    for plugin_name, plugin_api in cubeviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr), f"{attr} not in {plugin_name}"


def test_remote_server_disable_save_serverside():
    config = get_configuration('cubeviz')
    config['settings']['server_is_remote'] = True

    cubeviz_app = Application(config)
    cubeviz_helper = Cubeviz(cubeviz_app)
    exp = cubeviz_helper.plugins['Export']
    assert 'mp4' not in exp.viewer_format.choices

    mm = cubeviz_helper.plugins['Moment Maps']
    assert mm._obj.export_enabled is False


def test_get_data_spatial_and_spectral(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label="test")
    unit = spectrum1d_cube_larger.spectral_axis.unit
    subset_plugin = cubeviz_helper.plugins['Subset Tools']
    subset_plugin.import_region([
        EllipsePixelRegion(center=PixCoord(x=4.5, y=4), width=9, height=8),  # Subset 1 (spatial)
        SpectralRegion(4.62440061e-07 * unit, 4.62520112e-07 * unit),  # Subset 2 (spectral)
    ], combination_mode="new")
    spatial_with_spec = cubeviz_helper.get_data(data_label="Spectrum (Subset 1, sum)",
                                                spectral_subset="Subset 2")
    assert spatial_with_spec.flux.ndim == 1
    assert list(spatial_with_spec.mask) == [True, True, False, False, True,
                                            True, True, True, True, True]
    assert max(list(spatial_with_spec.flux.value)) == 232.
    assert min(list(spatial_with_spec.flux.value)) == 16.
