import pytest

from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from specutils import Spectrum1D

from glue.core.roi import XRangeROI


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


def test_invalid_function(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    cubeviz_helper._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

    with pytest.raises(ValueError, match='function 42 not in list of valid '):
        cubeviz_helper.get_data(data_label="test[FLUX]", spatial_subset='Subset 1', function=42)

    # Also make sure specviz redshift slider warning does not show up.
    # https://github.com/spacetelescope/jdaviz/issues/2029
    cubeviz_helper.specviz.y_limits(0, 3)


def test_valid_function(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    cubeviz_helper._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

    results_cube = cubeviz_helper.get_data(data_label="test[FLUX]",
                                           spatial_subset='Subset 1')
    assert results_cube.flux.ndim == 3
    results_false = cubeviz_helper.get_data(data_label="test[FLUX]",
                                            spatial_subset='Subset 1', function=False)
    assert results_false.flux.ndim == 3

    results_def = cubeviz_helper.get_data(data_label="test[FLUX]",
                                          spatial_subset='Subset 1', function=True)
    assert results_def.flux.ndim == 1

    results_min = cubeviz_helper.get_data(data_label="test[FLUX]",
                                          spatial_subset='Subset 1', function="minimum")
    results_max = cubeviz_helper.get_data(data_label="test[FLUX]",
                                          spatial_subset='Subset 1', function="maximum")
    assert isinstance(results_min, Spectrum1D)
    assert_quantity_allclose(results_min.flux,
                             [6., 14.] * u.Jy, atol=1e-5 * u.Jy)
    assert_quantity_allclose(results_max.flux,
                             [7., 15.] * u.Jy, atol=1e-5 * u.Jy)

    # calling without function gives cube
    assert cubeviz_helper.get_data(data_label="test[FLUX]").flux.ndim == 3
    # but calling through specviz automatically collapses
    assert cubeviz_helper.specviz.get_data(data_label="test[FLUX]").flux.ndim == 1


def test_get_data_spatial_and_spectral(cubeviz_helper, spectrum1d_cube_larger):
    data_label = "test"
    spatial_subset = "Subset 1"
    spectral_subset = "Subset 2"
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label)
    cubeviz_helper._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

    spec_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_spectrum_viewer_reference_name) # noqa
    spec_viewer.apply_roi(XRangeROI(4.62440061e-07, 4.62520112e-07))

    data_label = data_label + "[FLUX]"
    # This will be the same if function is None or True
    spatial_with_spec = cubeviz_helper.get_data(data_label=data_label,
                                                spatial_subset=spatial_subset,
                                                spectral_subset=spectral_subset)
    assert spatial_with_spec.flux.ndim == 1
    assert list(spatial_with_spec.mask) == [True, True, False, False, True,
                                            True, True, True, True, True]
    assert max(list(spatial_with_spec.flux.value)) == 157.
    assert min(list(spatial_with_spec.flux.value)) == 13.

    spatial_with_spec = cubeviz_helper.get_data(data_label=data_label,
                                                spatial_subset=spatial_subset,
                                                spectral_subset=spectral_subset,
                                                function='minimum')
    assert max(list(spatial_with_spec.flux.value)) == 78.
    assert min(list(spatial_with_spec.flux.value)) == 6.

    collapse_with_spectral = cubeviz_helper.get_data(data_label=data_label,
                                                     spectral_subset=spectral_subset,
                                                     function=True)
    collapse_with_spectral2 = cubeviz_helper.get_data(data_label=data_label,
                                                      function=True)

    assert list(collapse_with_spectral.flux) == list(collapse_with_spectral2.flux)

    with pytest.raises(ValueError, match=f'{spectral_subset} is not a spatial subset.'):
        cubeviz_helper.get_data(data_label=data_label, spatial_subset=spectral_subset,
                                function=True)
    with pytest.raises(ValueError, match=f'{spatial_subset} is not a spectral subset.'):
        cubeviz_helper.get_data(data_label=data_label, spectral_subset=spatial_subset,
                                function=True)
    with pytest.raises(ValueError, match='function cannot be False if spectral_subset'):
        cubeviz_helper.get_data(data_label=data_label, spectral_subset=spectral_subset,
                                function=False)
