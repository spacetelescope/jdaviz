"""Integration coverage for native spectral-line layers in spectrum viewers."""

import astropy.units as u
import numpy as np
import pytest
from astropy.table import QTable
from glue_jupyter.bqplot.common.line_layers import BqplotVerticalLineLayerArtist
from numpy.testing import assert_allclose
from specutils import Spectrum

from jdaviz.core.events import NewViewerMessage
from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer


@pytest.fixture
def line_helper(deconfigged_helper):
    deconfigged_helper._app.state.dev_spectral_lines_plugin = True
    return deconfigged_helper


def import_lines(helper, label, positions, **columns):
    """Use the object loader, leaving admission to the viewer's data menu."""
    loader = helper.loaders['object']
    loader.object = QTable({'wavelength': positions, **columns})
    loader.format = 'Spectral Lines'
    importer = loader.importer
    importer.data_label = label
    importer.viewer.create_new = ''
    if columns:
        importer.col_other = list(columns)
    importer()
    return helper._app.data_collection[label]


def empty_viewer(helper):
    # Test line rendering independently of viewer-creator UI relevancy.
    return helper._app._on_new_viewer(
        NewViewerMessage(Spectrum1DViewer, None, sender=helper._app), name='1D Spectrum'
    )


def line_artist(viewer, data):
    artists = [artist for artist in viewer.layers if artist.layer is data]
    assert len(artists) == 1
    artist = artists[0]
    assert isinstance(artist, BqplotVerticalLineLayerArtist)
    assert artist.enabled
    assert sum(mark is artist.line_mark for mark in viewer.figure.marks) == 1
    return artist


def assert_positions(artist, expected):
    """Check rendered coordinates, not only the generated data component."""
    x = np.asarray(artist.line_mark.x)
    assert_allclose(np.sort(x[np.isfinite(x)]), np.sort(np.repeat(expected, 2)))
    y = np.asarray(artist.line_mark.y)
    assert_allclose(np.unique(y[np.isfinite(y)]), [0, 1])
    assert artist.line_mark.scales['y'] is artist.scale_along_lines
    assert artist.scale_along_lines.min == 0
    assert artist.scale_along_lines.max == 1


@pytest.mark.parametrize('first_unit', [u.AA, u.nm])
def test_line_only_menu_units_home_and_visibility(line_helper, first_unit):
    viewer = empty_viewer(line_helper)
    first = import_lines(line_helper, 'first lines', ([6000, 6500] * u.AA).to(first_unit))
    second = import_lines(line_helper, 'second lines', [700, 800] * u.nm)
    menu = viewer.data_menu
    assert first.label in menu._obj.dataset.choices
    assert second.label in menu._obj.dataset.choices
    assert len(viewer.layers) == 0  # importing does not insert spectrum layers
    menu.add_data(first.label, second.label)

    assert viewer.state.reference_data is None
    assert u.Unit(viewer.state.x_display_unit) == first_unit
    assert viewer.state.y_display_unit is None
    assert viewer.data() == []
    assert_allclose([viewer.state.y_min, viewer.state.y_max], [0, 1])
    scale = (1 * u.AA).to_value(first_unit)
    first_artist = line_artist(viewer, first)
    second_artist = line_artist(viewer, second)
    assert_positions(first_artist, np.array([6000, 6500]) * scale)
    assert_positions(second_artist, np.array([7000, 8000]) * scale)

    viewer.state.x_min, viewer.state.x_max = 1, 2
    viewer.toolbar.tools['jdaviz:homezoom'].activate()
    assert_allclose([viewer.state.x_min, viewer.state.x_max], np.array([6000, 8000]) * scale)
    menu.set_layer_visibility(second.label, False)
    assert not second_artist.line_mark.visible
    viewer.toolbar.tools['jdaviz:homezoom'].activate()
    assert_allclose([viewer.state.x_min, viewer.state.x_max], np.array([6000, 6500]) * scale)
    menu.set_layer_visibility(second.label, True)
    assert second_artist.line_mark.visible
    viewer.toolbar.tools['jdaviz:homezoom'].activate()
    assert_allclose([viewer.state.x_min, viewer.state.x_max], np.array([6000, 8000]) * scale)


@pytest.mark.parametrize('display_unit', [None, 'Angstrom', 'nm', 'Hz'])
def test_shared_default_redshift_redraws_both_native_layers(
        line_helper, spectrum1d, display_unit):
    viewer = empty_viewer(line_helper)
    if display_unit is not None:
        line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    first = import_lines(line_helper, 'angstrom lines', [6562.8, 7000] * u.AA)
    second = import_lines(line_helper, 'nanometer lines', [486.13, 500] * u.nm)
    viewer.data_menu.add_data(first.label, second.label)
    if display_unit is not None:
        line_helper.plugins['Unit Conversion'].spectral_unit = display_unit
    first_artist, second_artist = line_artist(viewer, first), line_artist(viewer, second)
    first_mark, second_mark = first_artist.line_mark, second_artist.line_mark
    reference, x_att = viewer.state.reference_data, viewer.state.x_att
    limits = [viewer.state.x_min, viewer.state.x_max]
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component_selected = 'default'

    for redshift in (0.1, 0.5, 0):
        plugin.component_redshift = redshift
        assert first_artist.line_mark is first_mark
        assert second_artist.line_mark is second_mark
        for data, artist, rest in (
                (first, first_artist, [6562.8, 7000] * u.AA),
                (second, second_artist, [486.13, 500] * u.nm)):
            observed = rest * (1 + redshift)
            assert_allclose(data['observed wavelength:default'], observed.value)
            assert_positions(artist, observed.to_value(
                viewer.state.x_display_unit, equivalencies=u.spectral()))
        assert viewer.state.reference_data is reference
        assert viewer.state.x_att is x_att
        assert_allclose([viewer.state.x_min, viewer.state.x_max], limits)

    # Direct observed-column edits must redraw as well: no plugin-only refresh
    # or artificial axis/style change should be necessary.
    first.update_components({first.id['observed wavelength:default']: [6600, 7100]})
    assert_positions(first_artist, ([6600, 7100] * u.AA).to_value(
        viewer.state.x_display_unit, equivalencies=u.spectral()))


@pytest.mark.parametrize('lines_first', [True, False])
def test_spectrum_reference_and_frequency_display(line_helper, spectrum1d, lines_first):
    viewer = empty_viewer(line_helper)
    if lines_first:
        first = import_lines(line_helper, 'first lines', [6562.8, 7000] * u.AA)
        viewer.data_menu.add_data(first.label)
        assert viewer.state.reference_data is None

    line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    reference = line_helper._app.data_collection['spectrum']
    assert viewer.state.reference_data is reference
    x_att = viewer.state.x_att
    assert x_att in reference.components
    assert u.Unit(viewer.state.y_display_unit) == spectrum1d.flux.unit

    if not lines_first:
        first = import_lines(line_helper, 'first lines', [6562.8, 7000] * u.AA)
        viewer.data_menu.add_data(first.label)
    second = import_lines(line_helper, 'second lines', [486.13, 500] * u.nm)
    viewer.data_menu.add_data(second.label)
    assert viewer.state.reference_data is reference
    assert viewer.state.x_att is x_att
    assert_positions(line_artist(viewer, first), [6562.8, 7000])
    assert_positions(line_artist(viewer, second), [4861.3, 5000])

    line_helper.plugins['Unit Conversion'].spectral_unit = 'Hz'
    assert u.Unit(viewer.state.x_display_unit) == u.Hz
    assert_positions(line_artist(viewer, first),
                     ([6562.8, 7000] * u.AA).to_value(u.Hz, equivalencies=u.spectral()))
    assert_positions(line_artist(viewer, second),
                     ([486.13, 500] * u.nm).to_value(u.Hz, equivalencies=u.spectral()))
    assert viewer.state.reference_data is reference
    assert viewer.state.x_att is x_att


def test_remove_readd_has_no_duplicate_artists_or_marks(line_helper):
    viewer = empty_viewer(line_helper)
    data = import_lines(line_helper, 'lines', [6562.8, 7000] * u.AA)
    menu = viewer.data_menu
    menu.add_data(data.label)
    original_mark = line_artist(viewer, data).line_mark
    menu.add_data(data.label)
    assert line_artist(viewer, data).line_mark is original_mark
    menu.layer.selected = [data.label]
    menu.remove_from_viewer()
    assert not any(artist.layer is data for artist in viewer.layers)
    assert not any(mark is original_mark for mark in viewer.figure.marks)
    assert data in line_helper._app.data_collection
    menu.add_data(data.label)
    assert_positions(line_artist(viewer, data), [6562.8, 7000])


def test_last_spectrum_removal_and_table_deletion_preserve_other_lines(line_helper, spectrum1d):
    viewer = empty_viewer(line_helper)
    line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    first = import_lines(line_helper, 'first lines', [6562.8, 7000] * u.AA)
    second = import_lines(line_helper, 'second lines', [486.13, 500] * u.nm)
    viewer.data_menu.add_data(first.label, second.label)
    line_helper._app.data_item_remove('spectrum')
    assert viewer.state.reference_data is None
    assert viewer.state.y_display_unit is None
    assert viewer.data() == []
    assert_positions(line_artist(viewer, first), [6562.8, 7000])
    second_mark = line_artist(viewer, second).line_mark

    line_helper._app.data_item_remove(first.label)
    assert first not in line_helper._app.data_collection
    assert second in line_helper._app.data_collection
    assert line_artist(viewer, second).line_mark is second_mark
    assert viewer.state.reference_data is None
    assert_positions(line_artist(viewer, second), [4861.3, 5000])
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component_redshift = 0.1
    assert_positions(line_artist(viewer, second), np.array([4861.3, 5000]) * 1.1)


def test_frequency_input_rejected_without_deleting_table(line_helper):
    viewer = empty_viewer(line_helper)
    data = import_lines(line_helper, 'frequency lines', [4e14, 5e14] * u.Hz)
    assert data.label not in viewer.data_menu._obj.dataset.choices
    with pytest.raises(ValueError, match='not able to be loaded'):
        viewer.data_menu.add_data(data.label)
    assert data in line_helper._app.data_collection
    assert len(viewer.layers) == 0


@pytest.mark.parametrize('with_spectrum', [False, True])
def test_profile_consumers_skip_line_tables(line_helper, spectrum1d, with_spectrum):
    viewer = empty_viewer(line_helper)
    if with_spectrum:
        line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    # Deliberately include profile-like columns: these are still a line table.
    data = import_lines(line_helper, 'lines', [6562.8, 7000] * u.AA,
                        flux=[1, 2] * u.Jy, uncertainty=[0.1, 0.2] * u.Jy, mask=[0, 1])
    viewer.data_menu.add_data(data.label)
    spectra = viewer.data()
    assert len(spectra) == int(with_spectrum)
    assert all(isinstance(spectrum, Spectrum) for spectrum in spectra)
    if with_spectrum:
        assert_allclose(spectra[0].flux.value, spectrum1d.flux.value)
    artist = line_artist(viewer, data)
    mark = artist.line_mark
    viewer.state.show_uncertainty = True
    viewer.show_mask()
    assert viewer.state.show_uncertainty
    assert viewer.display_mask
    assert_positions(artist, [6562.8, 7000])
    viewer.clean()
    assert not viewer.state.show_uncertainty
    assert not viewer.display_mask
    assert artist.line_mark is mark
    assert any(candidate is mark for candidate in viewer.figure.marks)


@pytest.mark.parametrize('with_spectrum', [False, True])
def test_plot_options_line_layer_selection_smoke(line_helper, spectrum1d, with_spectrum):
    viewer = empty_viewer(line_helper)
    if with_spectrum:
        line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    first = import_lines(line_helper, 'first lines', [6562.8, 7000] * u.AA)
    second = import_lines(line_helper, 'second lines', [486.13, 500] * u.nm)
    viewer.data_menu.add_data(first.label, second.label)
    options = line_helper._app.get_tray_item_from_name('g-plot-options')
    options.viewer.selected = '1D Spectrum'
    options.plugin_opened = True
    for data in (first, second):
        options.layer.selected = data.label
        assert options.layer.selected == data.label
        assert line_artist(viewer, data).line_mark.visible


@pytest.mark.parametrize('with_spectrum', [False, True])
def test_component_layers_independent_updates_and_controls(line_helper, spectrum1d, with_spectrum):
    from jdaviz.core.spectral_line_layers import component_datasets

    viewer = empty_viewer(line_helper)
    if with_spectrum:
        line_helper.load(spectrum1d, format='1D Spectrum', data_label='spectrum')
    source = import_lines(line_helper, 'lines', [6000, 6500] * u.AA)
    viewer.data_menu.add_data(source.label)
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component.add_choice('second')
    plugin.component_redshift = 0.1
    second = next(iter(component_datasets(source).values()))
    assert second.label == 'lines [second]'
    assert second.label in viewer.data_menu.layer.choices
    first_artist, second_artist = line_artist(viewer, source), line_artist(viewer, second)
    assert_positions(first_artist, [6000, 6500])
    assert_positions(second_artist, [6600, 7150])

    options = line_helper._app.get_tray_item_from_name('g-plot-options')
    options.viewer.selected = '1D Spectrum'
    options.plugin_opened = True
    assert source.label in options.layer.choices
    assert second.label in options.layer.choices
    options.layer.selected = second.label
    options.line_color.value = '#ff0000'
    options.line_width.value = 4
    options.line_opacity.value = 0.4
    assert second_artist.state.color == '#ff0000'
    assert second_artist.state.linewidth == 4
    assert second_artist.state.alpha == 0.4
    assert first_artist.state.linewidth != 4
    viewer.data_menu.set_layer_visibility(second.label, False)
    assert not second_artist.line_mark.visible
    assert first_artist.line_mark.visible

    source.update_components({source.id['observed wavelength:second']: [7000, 7500]})
    assert_positions(second_artist, [7000, 7500])
    assert_positions(first_artist, [6000, 6500])
    assert not second_artist.line_mark.visible
    viewer.data_menu.set_layer_visibility(second.label, True)
    if with_spectrum:
        line_helper.plugins['Unit Conversion'].spectral_unit = 'Hz'
        assert_positions(second_artist, ([7000, 7500] * u.AA).to_value(u.Hz, u.spectral()))

    mark = second_artist.line_mark
    plugin.component.rename_choice('second', 'renamed')
    assert second.label == 'lines [renamed]'
    assert second.label in viewer.data_menu.layer.choices
    assert second.label in options.layer.choices
    assert second_artist.line_mark is mark
    assert second_artist.state.linewidth == 4
    plugin.component_redshift = 0.2
    assert_positions(second_artist, ([7200, 7800] * u.AA).to_value(
        viewer.state.x_display_unit, u.spectral()))
    plugin.component.remove_choice('renamed')
    assert second not in line_helper._app.data_collection
    assert not any(candidate is mark for candidate in viewer.figure.marks)
    assert source.label in viewer.data_menu.layer.choices


def test_components_created_before_plot_and_multiple_tables(line_helper):
    from jdaviz.core.spectral_line_layers import component_datasets

    viewer = empty_viewer(line_helper)
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component.add_choice('second')
    plugin.component_redshift = 0.1
    first = import_lines(line_helper, 'first', [6000, 6500] * u.AA)
    second = import_lines(line_helper, 'second', [500, 550] * u.nm)
    assert component_datasets(first) == {}
    viewer.data_menu.add_data(first.label, second.label)
    extra_first = next(iter(component_datasets(first).values()))
    extra_second = next(iter(component_datasets(second).values()))
    assert_positions(line_artist(viewer, extra_first), [6600, 7150])
    assert_positions(line_artist(viewer, extra_second), [5500, 6050])
    plugin.component_redshift = 0.2
    assert_positions(line_artist(viewer, extra_first), [7200, 7800])
    assert_positions(line_artist(viewer, extra_second), [6000, 6600])
    plugin.component_selected = 'default'
    plugin.component_redshift = 0.3
    assert_positions(line_artist(viewer, first), [7800, 8450])
    assert_positions(line_artist(viewer, extra_first), [7200, 7800])
    line_helper._app.rename_data(first.label, 'renamed source')
    assert extra_first.label == 'renamed source [second]'
    line_helper._app.data_item_remove(first.label)
    assert extra_first not in line_helper._app.data_collection
    assert extra_second in line_helper._app.data_collection
    assert_positions(line_artist(viewer, extra_second), [6000, 6600])


def test_component_layer_multiple_viewers_and_explicit_removal(line_helper):
    from jdaviz.core.spectral_line_layers import component_datasets

    first_viewer = empty_viewer(line_helper)
    source = import_lines(line_helper, 'lines', [6000, 6500] * u.AA)
    first_viewer.data_menu.add_data(source.label)
    second_viewer = line_helper._app._on_new_viewer(
        NewViewerMessage(Spectrum1DViewer, None, sender=line_helper._app), name='Other spectrum')
    second_viewer.data_menu.add_data(source.label)
    second_viewer.state.x_display_unit = 'nm'
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component.add_choice('second')
    extra = next(iter(component_datasets(source).values()))
    assert_positions(line_artist(first_viewer, extra), [6000, 6500])
    assert_positions(line_artist(second_viewer, extra), [600, 650])
    first_viewer.data_menu.layer.selected = [extra.label]
    first_viewer.data_menu.remove_from_viewer()
    plugin.component_redshift = 0.1
    assert not any(artist.layer is extra for artist in first_viewer.layers)
    assert_positions(line_artist(second_viewer, extra), [660, 715])
    first_viewer.data_menu.add_data(extra.label)
    assert_positions(line_artist(first_viewer, extra), [6600, 7150])


def test_primary_component_rename_preserves_layer(line_helper):
    viewer = empty_viewer(line_helper)
    source = import_lines(line_helper, 'lines', [6000, 6500] * u.AA)
    viewer.data_menu.add_data(source.label)
    artist = line_artist(viewer, source)
    mark = artist.line_mark
    plugin = line_helper._app.get_tray_item_from_name('g-spectral-lines')
    plugin.component.rename_choice('default', 'primary')
    plugin.component_redshift = 0.1
    assert artist.line_mark is mark
    assert_positions(artist, [6600, 7150])
    plugin.component.add_choice('second')
    plugin.component.remove_choice('primary')
    assert_positions(line_artist(viewer, source), [6000, 6500])
