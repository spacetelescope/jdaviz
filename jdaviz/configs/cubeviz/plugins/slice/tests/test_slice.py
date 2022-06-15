import pytest
import numpy as np

from jdaviz.configs.cubeviz.plugins.slice.slice import Slice


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_slice(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    sl = Slice(app=app)
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")

    # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
    assert sl.slider == 1
    cubeviz_helper.select_slice(0)
    assert sl.slider == 0

    with pytest.raises(
            TypeError,
            match="slice must be an integer"):
        cubeviz_helper.select_slice("blah")

    with pytest.raises(
            ValueError,
            match="slice must be positive"):
        cubeviz_helper.select_slice(-5)

    cubeviz_helper.select_wavelength(4.62360028e-07)
    assert sl.slider == 1

    # from the widget this logic is duplicated (to avoid sending logic through messages)
    sl.vue_change_wavelength('4.62e-07')
    assert sl.slider == 0
    assert np.allclose(sl.wavelength, 4.62280007e-07)

    # make sure that passing an invalid value from the UI would revert to the previous value
    # JS strips invalid characters, but doesn't ensure its float-compatible
    sl.vue_change_wavelength('1.2.3')
    assert sl.slider == 0

    # there is only one watched viewer, since the uncertainty/mask viewers are empty
    assert len(sl._watched_viewers) == 1
    assert len(sl._indicator_viewers) == 1

    # test setting a static 2d image to the "watched" flux viewer to make sure it disconnects
    mm = app.get_tray_item_from_name('cubeviz-moment-maps')
    mm.add_to_viewer_selected = 'flux-viewer'
    mm.vue_calculate_moment()

    assert len(sl._watched_viewers) == 1
    assert len(sl._indicator_viewers) == 1


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_indicator_settings(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")
    sl = Slice(app=app)
    sv = app.get_viewer('spectrum-viewer')
    indicator = sv.slice_indicator

    assert sl.setting_show_indicator is True
    assert indicator._show_if_inactive is True
    assert sl.setting_show_wavelength is True
    assert indicator.label.visible is True

    sl.setting_show_indicator = False
    assert indicator._show_if_inactive is False

    sl.setting_show_wavelength = False
    assert indicator.label.visible is False
