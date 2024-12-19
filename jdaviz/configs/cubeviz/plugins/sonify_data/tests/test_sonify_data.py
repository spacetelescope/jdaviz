import os

import astropy.units as u
import pytest
from specutils import SpectralRegion

pytest.importorskip("strauss")
IN_GITHUB_ACTIONS = os.environ.get("CI", "false") == "true"


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test requires computer with audio output.")
def test_sonify_data(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label="test")
    sonify_plg = cubeviz_helper.app.get_tray_item_from_name('cubeviz-sonify-data')
    assert sonify_plg.stream_active

    # Create sonified data cube
    sonify_plg.vue_sonify_cube()
    assert sonify_plg.flux_viewer.sonification_wl_bounds is None
    assert sonify_plg.flux_viewer.sonified_cube is not None

    # Test changing volume
    sonify_plg.volume = 90
    assert sonify_plg.flux_viewer.volume_level == 90

    # Test using spectral subset for setting sonification bounds
    spec_region = SpectralRegion(4.62360028e-07*u.m, 4.62920561e-07*u.m)
    subset_plugin = cubeviz_helper.plugins['Subset Tools']._obj
    subset_plugin.import_region(spec_region)
    sonify_plg.spectral_subset_selected = 'Subset 1'
    sonify_plg.vue_sonify_cube()
    assert sonify_plg.flux_viewer.sonification_wl_bounds == (4.62360028e-07, 4.62920561e-07)

    # Stop/start stream
    sonify_plg.vue_start_stop_stream()
    assert sonify_plg.flux_viewer.stream_active is False
    sonify_plg.vue_start_stop_stream()
    assert sonify_plg.flux_viewer.stream_active


@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Plugin disabled only in CI")
def test_sonify_data_disabled(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label="test")
    sonify_plg = cubeviz_helper.app.get_tray_item_from_name('cubeviz-sonify-data')
    assert sonify_plg.disabled_msg
    with pytest.raises(ValueError, match='Unable to sonify cube'):
        sonify_plg.vue_sonify_cube()
