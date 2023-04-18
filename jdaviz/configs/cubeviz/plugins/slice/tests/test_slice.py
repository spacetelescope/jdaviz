import warnings

import pytest
import numpy as np

from jdaviz.configs.cubeviz.plugins.slice.slice import Slice


def test_slice(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    sl = Slice(app=app)

    # Make sure nothing crashes if plugin used without data
    sl.vue_play_next()
    assert sl.slice == 0
    sl.vue_play_start_stop()
    assert not sl.is_playing
    assert not sl._player

    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")
    app.add_data_to_viewer("uncert-viewer", "test")

    # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
    assert sl.slice == 1
    assert cubeviz_helper.app.get_viewer("flux-viewer").state.slices[-1] == 1
    assert cubeviz_helper.app.get_viewer("uncert-viewer").state.slices[-1] == 1
    cubeviz_helper.select_slice(0)
    assert sl.slice == 0

    with pytest.raises(
            TypeError,
            match="slice must be an integer"):
        cubeviz_helper.select_slice("blah")

    with pytest.raises(
            ValueError,
            match="slice must be positive"):
        cubeviz_helper.select_slice(-5)

    cubeviz_helper.select_wavelength(4.62360028e-07)
    assert sl.slice == 1

    # from the widget this logic is duplicated (to avoid sending logic through messages)
    sl._on_wavelength_updated({'new': '4.62e-07'})
    assert sl.slice == 0
    assert np.allclose(sl.wavelength, 4.62280007e-07)

    # make sure that passing an invalid value from the UI would revert to the previous value
    # JS strips invalid characters, but doesn't ensure its float-compatible
    sl._on_wavelength_updated({'new': '1.2.3'})
    assert sl.slice == 0

    assert len(sl._watched_viewers) == 2  # flux-viewer, uncert-viewer
    assert len(sl._indicator_viewers) == 1  # spectrum-viewer

    # test setting a static 2d image to the "watched" flux viewer to make sure it disconnects
    mm = app.get_tray_item_from_name('cubeviz-moment-maps')
    mm.add_to_viewer_selected = 'flux-viewer'
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message=r'.*No observer defined on WCS.*')
        mm.vue_calculate_moment()

    assert len(sl._watched_viewers) == 2
    assert len(sl._indicator_viewers) == 1

    # test in conjunction with as_steps
    sv = app.get_viewer('spectrum-viewer')
    orig_len = len(sv.native_marks[0].x)

    sv.state.layers[0].as_steps = True
    new_len = len(sv.native_marks[0].x)
    assert new_len == 2*orig_len
    cubeviz_helper.select_wavelength(4.62360028e-07)
    assert sl.slice == 1

    # Test player buttons API

    sl.vue_goto_first()
    assert sl.slice == 0

    sl.vue_goto_last()
    assert sl.slice == sl.max_value

    sl.vue_play_next()  # Should automatically wrap to beginning
    assert sl.slice == 0

    sl.vue_play_start_stop()  # Start
    assert sl.is_playing
    assert sl._player.is_alive()
    sl.vue_play_next()  # Should be no-op
    sl.vue_goto_last()  # Should be no-op
    sl.vue_goto_first()  # Should be no-op
    sl.vue_play_start_stop()  # Stop
    assert not sl.is_playing
    assert not sl._player
    # NOTE: Hard to check sl.slice here because it is non-deterministic.


def test_indicator_settings(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")
    sl = Slice(app=app)
    sv = app.get_viewer('spectrum-viewer')
    indicator = sv.slice_indicator

    assert sl.show_indicator is True
    assert indicator._show_if_inactive is True
    assert sl.show_wavelength is True
    assert indicator.label.visible is True

    sl.show_indicator = False
    assert indicator._show_if_inactive is False

    sl.show_wavelength = False
    assert indicator.label.visible is False


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_init_slice(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    sl = cubeviz_helper.plugins['Slice']
    assert sl.slice == 1
    assert fv.state.slices == (0, 0, 1)

    # make sure adding new data doesn't revert slice to 0
    mm = cubeviz_helper.plugins['Moment Maps']
    mm.calculate_moment(add_data=True)

    assert sl.slice == 1
    assert fv.state.slices == (0, 0, 1)
