import os

import astropy.units as u
from numpy.testing import assert_allclose
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
    assert sonify_plg.sonification_wl_ranges is None
    assert sonify_plg.sonified_cube is not None

    # Test changing volume
    sonify_plg.volume = 90
    assert sonify_plg.flux_viewer.volume_level == 90

    # Test using spectral subset for setting sonification bounds
    spec_region = SpectralRegion(4.62360028e-07*u.m, 4.62920561e-07*u.m)
    subset_plugin = cubeviz_helper.plugins['Subset Tools']._obj
    subset_plugin.import_region(spec_region)
    sonify_plg.spectral_subset_selected = 'Subset 1'
    sonify_plg.vue_sonify_cube()
    ranges = (sonify_plg.sonification_wl_ranges[0][0].value,
              sonify_plg.sonification_wl_ranges[0][1].value)
    assert ranges == (4.62360028e-07, 4.62920561e-07)

    # Stop/start stream
    sonify_plg.vue_start_stop_stream()
    assert sonify_plg.stream_active is False
    sonify_plg.vue_start_stop_stream()
    assert sonify_plg.stream_active

    # Add sonified data to uncert-viewer
    uncert_viewer = cubeviz_helper.viewers['uncert-viewer']._obj
    uncert_viewer.data_menu.add_data('Sonified data')
    assert 'Sonified data' in uncert_viewer.data_menu.data_labels_loaded

    event_data = {'event': 'mousemove', 'domain': {'x': 1, 'y': 1}}
    uncert_viewer._viewer_mouse_event(event_data)

    compsig = uncert_viewer.combined_sonified_grid[(1, 1)]
    sigmax = abs(compsig).max()
    INT_MAX = 2**15 - 1
    if sigmax > INT_MAX:
        compsig = ((INT_MAX/abs(compsig).max()) * compsig)
    assert_allclose(sonify_plg.sonified_cube.newsig, compsig)


@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Plugin disabled only in CI")
def test_sonify_data_disabled(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label="test")
    sonify_plg = cubeviz_helper.app.get_tray_item_from_name('cubeviz-sonify-data')
    assert sonify_plg.disabled_msg
    with pytest.raises(ValueError, match='Unable to sonify cube'):
        sonify_plg.vue_sonify_cube()
