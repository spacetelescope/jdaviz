import pytest

from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from specutils import Spectrum1D


def test_nested_helper(cubeviz_helper):
    '''Ensures the Cubeviz helper is always returned, even after the Specviz helper is called'''
    # Force Specviz helper to instantiate
    cubeviz_helper.specviz

    assert cubeviz_helper.app._jdaviz_helper == cubeviz_helper

    # The viewers also have a callthrough to the app's _jdaviz_helper attribute
    spec_viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')
    assert spec_viewer.jdaviz_helper == cubeviz_helper


def test_plugin_user_apis(cubeviz_helper):
    for plugin_name, plugin_api in cubeviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_invalid_statistic(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    cubeviz_helper._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

    with pytest.raises(ValueError, match='statistic 42 not in list of valid '):
        cubeviz_helper.get_data(data_label="test[FLUX]", subset_to_apply='Subset 1', statistic=42)


def test_valid_statistic(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    cubeviz_helper._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

    results_min = cubeviz_helper.get_data(data_label="test[FLUX]",
                                          subset_to_apply='Subset 1', statistic="minimum")
    results_max = cubeviz_helper.get_data(data_label="test[FLUX]",
                                          subset_to_apply='Subset 1', statistic="maximum")
    assert isinstance(results_min, Spectrum1D)
    assert_quantity_allclose(results_min.flux,
                             [6., 14.] * u.Jy, atol=1e-5 * u.Jy)
    assert_quantity_allclose(results_max.flux,
                             [7., 15.] * u.Jy, atol=1e-5 * u.Jy)
