import pytest
from regions import EllipsePixelRegion, PixCoord
from specutils import SpectralRegion

from jdaviz import Cubeviz
from jdaviz.app import PrivateApplication
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

    cubeviz_app = PrivateApplication(config)
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
    spatial_with_spec = cubeviz_helper.datasets["Spectrum (Subset 1, sum)"].get_data(
                                                spectral_subset="Subset 2")
    assert spatial_with_spec.flux.ndim == 1
    assert list(spatial_with_spec.mask) == [True, True, False, False, True,
                                            True, True, True, True, True]
    assert max(list(spatial_with_spec.flux.value)) == 157.
    assert min(list(spatial_with_spec.flux.value)) == 13.


def test_prevent_multiple_flux_cubes(cubeviz_helper, spectrum1d_cube):
    """Test that only one 3D spectrum (flux cube) can be loaded at a time."""
    # Load the first flux cube successfully
    cubeviz_helper.load(spectrum1d_cube, format='3D Spectrum')

    # Verify the cube was loaded
    assert len(cubeviz_helper.app.data_collection) == 2  # flux cube + auto-extracted spectrum
    assert cubeviz_helper.app._jdaviz_helper._loaded_flux_cube is not None

    # Store the label of the loaded flux cube
    flux_cube_label = cubeviz_helper.app._jdaviz_helper._loaded_flux_cube.label

    # Try to load a second cube via API - should raise ValueError
    with pytest.raises(ValueError,
                       match="Only a single 3D spectrum.*flux cube.*can be loaded into cubeviz"):
        cubeviz_helper.load(spectrum1d_cube, format='3D Spectrum', data_label='second_cube')

    # Verify data collection hasn't changed (still only 2 items)
    assert len(cubeviz_helper.app.data_collection) == 2

    # Now remove the flux cube from data collection
    # First find the flux cube data object
    flux_cube_data = cubeviz_helper.app._jdaviz_helper._loaded_flux_cube

    # Remove it from viewers
    cubeviz_helper.app.remove_data_from_viewer('flux-viewer', flux_cube_label)

    # Remove it from data collection
    cubeviz_helper.app.data_collection.remove(flux_cube_data)

    # Verify it's removed
    assert flux_cube_data not in cubeviz_helper.app.data_collection

    # Should now be able to load another cube via API (since the first was removed)
    cubeviz_helper.load(spectrum1d_cube, format='3D Spectrum', data_label='new_cube')

    # After reloading, we should have the new flux cube (data_label="new_cube")
    # and its auto-extracted spectrum
    all_labels = [d.label for d in cubeviz_helper.app.data_collection]
    assert 'new_cube' in all_labels, f"Expected 'new_cube' in data collection, found: {all_labels}" # noqa
    assert 'new_cube (sum)' in all_labels, f"Expected auto-extracted spectrum in data collection, found: {all_labels}"  # noqa
