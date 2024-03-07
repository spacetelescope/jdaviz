import warnings

import pytest

from jdaviz.configs.cubeviz.plugins.slice.slice import Slice


def test_slice(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    sl = Slice(app=app)

    # No data yet
    assert len(sl.slice_selection_viewers) == 2  # flux-viewer, uncert-viewer
    assert len(sl.slice_indicator_viewers) == 1  # spectrum-viewer
    assert len(sl.valid_indicator_values_sorted) == 0
    assert len(sl.valid_selection_values_sorted) == 0

    # Make sure nothing crashes if plugin used without data]
    sl.vue_play_next()
    sl.vue_play_start_stop()
    assert not sl.is_playing

    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    app.add_data_to_viewer("spectrum-viewer", "test[FLUX]")
    app.add_data_to_viewer("flux-viewer", "test[FLUX]")
    app.add_data_to_viewer("uncert-viewer", "test[FLUX]")

    # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
    assert len(sl.valid_indicator_values_sorted) == 2
    slice_values = sl.valid_selection_values_sorted
    assert len(slice_values) == 2

    assert sl.value == slice_values[1]
    assert cubeviz_helper.app.get_viewer("flux-viewer").slice == 1
    assert cubeviz_helper.app.get_viewer("flux-viewer").state.slices[-1] == 1
    assert cubeviz_helper.app.get_viewer("uncert-viewer").state.slices[-1] == 1
    cubeviz_helper.select_wavelength(slice_values[0])
    assert cubeviz_helper.app.get_viewer("flux-viewer").slice == 0
    assert sl.value == slice_values[0]

    cubeviz_helper.select_wavelength(slice_values[1])
    assert sl.value == slice_values[1]

    # test setting a static 2d image to the "watched" flux viewer to make sure it disconnects
    mm = app.get_tray_item_from_name('cubeviz-moment-maps')
    mm.add_to_viewer_selected = 'flux-viewer'
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message=r'.*No observer defined on WCS.*')
        mm.vue_calculate_moment()

    # test in conjunction with as_steps
    sv = app.get_viewer('spectrum-viewer')
    orig_len = len(sv.native_marks[0].x)

    sv.state.layers[0].as_steps = True
    new_len = len(sv.native_marks[0].x)
    assert new_len == 2*orig_len
    cubeviz_helper.select_wavelength(4.62360028e-07)
    assert sl.value == slice_values[1]

    # Test player buttons API

    sl.vue_goto_first()
    assert sl.value == slice_values[0]

    sl.vue_goto_last()
    assert sl.value == slice_values[-1]

    sl.vue_play_next()  # Should automatically wrap to beginning
    assert sl.value == slice_values[0]

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
    assert sl.show_value is True
    assert indicator.label.visible is True

    sl.show_indicator = False
    assert indicator._show_if_inactive is False

    sl.show_value = False
    assert indicator.label.visible is False


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_init_slice(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    sl = cubeviz_helper.plugins['Slice']
    slice_values = sl._obj.valid_selection_values_sorted

    assert sl.value == slice_values[1]
    assert fv.slice == 1
    assert fv.state.slices == (0, 0, 1)

    # make sure adding new data doesn't revert slice to 0
    mm = cubeviz_helper.plugins['Moment Maps']
    mm.calculate_moment(add_data=True)

    assert sl.value == slice_values[1]
    assert fv.slice == 1
    assert fv.state.slices == (0, 0, 1)
