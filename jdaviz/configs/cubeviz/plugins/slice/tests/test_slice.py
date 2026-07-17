import warnings
import pytest

from jdaviz.configs.cubeviz.plugins.slice.slice import SpectralSlice


def test_slice(deconfigged_helper, spectrum1d_cube):
    app = deconfigged_helper._app
    sl = SpectralSlice(app=app)

    # No data yet, so make sure all the lists are empty
    assert len(sl.slice_selection_viewers) == 0
    assert len(sl.slice_indicator_viewers) == 0
    assert len(sl.valid_indicator_values_sorted) == 0
    assert len(sl.valid_selection_values_sorted) == 0

    # Make sure nothing crashes if plugin used without data]
    sl.vue_play_next()
    sl.vue_play_start_stop()
    assert not sl.is_playing

    deconfigged_helper.load(spectrum1d_cube, data_label='test', format='3D Spectrum')
    app.add_data_to_viewer("3D Spectrum", "test")
    app.add_data_to_viewer("3D Spectrum", "test")
    app.add_data_to_viewer("1D Spectrum", "test (sum)")
    sv = deconfigged_helper.viewers['3D Spectrum']._obj.glue_viewer

    # data loaded, so object should have 2 slice selection viewers
    # and 1 slice indicator viewer
    assert len(sl.slice_selection_viewers) == 1  # one flux viewer
    assert len(sl.slice_indicator_viewers) == 1  # 3D Spectrum
    assert len(sl.valid_indicator_values_sorted) == 2
    assert len(sl.valid_selection_values_sorted) == 2

    # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
    assert len(sv.slice_values) == 2
    assert len(sl.valid_indicator_values_sorted) == 2
    slice_values = sl.valid_selection_values_sorted
    assert len(slice_values) == 2

    assert sl.value == slice_values[1]
    assert deconfigged_helper._app.get_viewer("3D Spectrum").slice == 1
    assert deconfigged_helper._app.get_viewer("3D Spectrum").state.slices[0] == 1
    assert deconfigged_helper._app.get_viewer("3D Spectrum").state.slices[0] == 1
    sl.value = slice_values[0]
    assert deconfigged_helper._app.get_viewer("3D Spectrum").slice == 0
    assert sl.value == slice_values[0]

    sl.value = slice_values[1]
    assert sl.value == slice_values[1]

    # test setting a static 2d image to the "watched" flux viewer to make sure it disconnects
    mm = app.get_tray_item_from_name('Moment Maps')
    mm.add_to_viewer_selected = '3D Spectrum'
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message=r'.*No observer defined on WCS.*')
        mm.vue_calculate_moment()

    # test in conjunction with as_steps
    sv = app.get_viewer('1D Spectrum')
    orig_len = len(sv.native_marks[0].x)

    sv.state.layers[0].as_steps = True
    new_len = len(sv.native_marks[0].x)
    assert new_len == 2*orig_len
    sl.value = 4.62360028e-07
    assert sl.value == slice_values[1]

    # Add test for unit conversion
    uc_plugin = deconfigged_helper.plugins['Unit Conversion']._obj
    uc_plugin.spectral_unit.selected = 'Angstrom'
    assert sl.value_unit == 'Angstrom'
    sl.value = 4623.60028
    assert sl.value == 4623.600276968349

    # Retrieve updated slice_values
    slice_values = sl.valid_selection_values_sorted

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


def test_indicator_settings(deconfigged_helper, spectrum1d_cube):
    deconfigged_helper.load(spectrum1d_cube, data_label='test', format='3D Spectrum')
    app = deconfigged_helper._app
    app.add_data_to_viewer("3D Spectrum", "test")
    app.add_data_to_viewer("1D Spectrum", "test (sum)")
    sl = deconfigged_helper.plugins['Spectral Slice']._obj
    sv = app.get_viewer('1D Spectrum')
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
def test_init_slice(deconfigged_helper, spectrum1d_cube):
    deconfigged_helper.load(spectrum1d_cube, data_label='test', format='3D Spectrum')

    fv = deconfigged_helper._app.get_viewer('3D Spectrum')
    sl = deconfigged_helper.plugins['Spectral Slice']._obj
    slice_values = sl.valid_selection_values_sorted

    assert sl.value == slice_values[1]
    assert fv.slice == 1
    assert fv.state.slices == (1, 0, 0)

    # make sure adding new data doesn't revert slice to 0
    mm = deconfigged_helper.plugins['Moment Maps']._obj
    mm.calculate_moment(add_data=True)

    assert sl.value == slice_values[1]
    assert fv.slice == 1
    assert fv.state.slices == (1, 0, 0)
