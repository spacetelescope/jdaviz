import pytest
import numpy as np
from astropy import units as u
from astropy.table import QTable
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose
from regions import RectanglePixelRegion, PixCoord
from specutils import Spectrum, SpectralRegion
from glue.core.roi import XRangeROI

from jdaviz.configs.specviz.plugins.line_analysis.line_analysis import _coerce_unit
from jdaviz.core.custom_units_and_equivs import PIX2
from jdaviz.core.events import LineIdentifyMessage
from jdaviz.core.marks import LineAnalysisContinuum


def test_plugin(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # disabling keep_active should hide the continuum
    plugin.keep_active = False
    assert np.all([cm.visible is False for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.selected_subset = 'Subset 1'
    plugin.selected_continuum = 'Surrounding'
    plugin.width = 3

    for result_dict in plugin.get_results():
        if result_dict in ['Line Flux']:
            # should have an assigned uncertainty (with min required version of specutils)
            assert len(result_dict.get('uncertainty')) > 0

    assert len(plugin.table) == 1


@pytest.mark.filterwarnings(r"ignore:'W/m2/m' contains multiple slashes")
@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_spatial_subset(cubeviz_helper, image_cube_hdu_obj):
    """
    Tests that the spatial selection returns any valid result, DOES NOT VALIDATE THE VALUE
    Not checking the value attempts to circumvent the issue we ran into here:
    https://github.com/spacetelescope/jdaviz/pull/1564#discussion_r949427663
    """
    cubeviz_helper.load_data(image_cube_hdu_obj, data_label="Test Cube")

    # add a spatial region
    cubeviz_helper.plugins['Subset Tools'].import_region(
        RectanglePixelRegion(center=PixCoord(x=3, y=5), width=4, height=6))

    # create a spectral region
    unit = u.Unit(cubeviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    cubeviz_helper.plugins['Subset Tools'].combination_mode = 'new'
    cubeviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(3.623e-7 * unit,
                                                                        3.627e-7 * unit))
    cubeviz_helper.app.state.drawer_content = 'plugins'

    plugin = cubeviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    plugin.dataset_selected = 'Spectrum (Subset 1, sum)'
    plugin.spectral_subset_selected = 'Subset 2'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 1

    for result in plugin.get_results():
        # Check that there exists a value
        assert not np.isnan(float(result['result']))
        # Check the unit is not dimensionless
        assert u.Unit(result['unit']) != u.dimensionless_unscaled


@pytest.mark.parametrize('sq_angle_unit', [u.sr, PIX2])
def test_cubeviz_units(cubeviz_helper, spectrum1d_cube_custom_fluxunit,
                       sq_angle_unit):
    """
    Tests that the plugin produces the correct result when loaded cube
    is in flux/pix2 and flux/sr, and that the results remain consistant
    between translations of the spectral y axis flux<>surface brightness.
    """
    cube = spectrum1d_cube_custom_fluxunit(fluxunit=u.Jy / sq_angle_unit,
                                           shape=(25, 25, 4), with_uncerts=True)
    cubeviz_helper.load_data(cube, data_label="Test Cube")

    uc = cubeviz_helper.plugins['Unit Conversion']
    assert uc.spectral_y_type == 'Flux'  # initial selection should be Flux

    plugin = cubeviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    plugin.dataset_selected = 'Spectrum (sum)'
    plugin.continuum_subset_selected = 'Surrounding'

    results = plugin.get_results()
    assert results[0]['unit'] == 'W / m2'

    viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')
    viewer.apply_roi(XRangeROI(4.63e-7, 4.64e-7))

    la = cubeviz_helper.plugins['Line Analysis']
    la.keep_active = True
    la.spectral_subset.selected = 'Subset 1'

    marks_before = [la._obj.continuum_marks['left'].marks_list[0].y,
                    la._obj.continuum_marks['right'].marks_list[0].y]

    # change flux unit and make sure result stays the same after conversion
    uc.flux_unit.selected = 'MJy'

    marks_after = [la._obj.continuum_marks['left'].marks_list[0].y,
                   la._obj.continuum_marks['right'].marks_list[0].y]

    # ensure continuum marks update when spectral_y is changed by
    # multiply converted continuum marks by expected scale factor (MJy -> Jy)
    scaling_factor = 1e-6
    assert_allclose([mark * scaling_factor for mark in marks_before], marks_after, rtol=1e-5)

    # reset to test again after spectral_y_type is changed
    marks_before = marks_after

    # now change to surface brightness
    uc.spectral_y_type = 'Surface Brightness'

    if sq_angle_unit == PIX2:
        # translation does not alter spectral_y values in viewer
        scaling_factor = 1
    else:
        scaling_factor = cube.meta.get('PIXAR_SR')

    marks_after = [la._obj.continuum_marks['left'].marks_list[0].y,
                   la._obj.continuum_marks['right'].marks_list[0].y]

    # ensure continuum marks update when spectral_y_type is changed
    # multiply converted continuum marks by expected pixel scale factor
    assert_allclose([mark / scaling_factor for mark in marks_before], marks_after, rtol=1e-5)

    results = plugin.get_results()
    line_flux_before_unit_conversion = results[0]
    # convert back and forth between unit<>str for string format consistency
    unit_str = u.Unit(f'W / {sq_angle_unit.to_string()} m2').to_string()
    assert line_flux_before_unit_conversion['unit'] == unit_str

    # change flux unit and make sure result stays the same after conversion
    uc.flux_unit.selected = 'MJy'
    results = plugin.get_results()
    np.testing.assert_allclose(float(results[0]['result']),
                               float(line_flux_before_unit_conversion['result']))
    np.testing.assert_allclose(float(results[0]['uncertainty']),
                               float(line_flux_before_unit_conversion['uncertainty']))


def test_user_api(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))

    la = specviz_helper.plugins['Line Analysis']
    la.keep_active = True

    # spectral subset now supports multiselect
    assert "multiselect" in la.spectral_subset.__repr__()
    with pytest.raises(ValueError):
        la.spectral_subset.select_all()
    with pytest.raises(ValueError):
        la.spectral_subset.select_none()

    # test that setting a string to a Selection component redirects to the selected traitlet
    la.spectral_subset = 'Subset 1'
    assert la.spectral_subset.selected == 'Subset 1'

    # test that invalid strings are caught and reverted to the original selection
    with pytest.raises(ValueError):
        la.spectral_subset = 'invalid'

    assert la.spectral_subset.selected == 'Subset 1'

    la.get_results()


def test_line_identify(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
    lt['listname'] = 'Test List'
    specviz_helper.load_line_list(lt)

    ll_plugin = specviz_helper.app.get_tray_item_from_name('g-line-list')
    la_plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    la_plugin.get_results()
    rest_names = [line['name_rest'] for line in ll_plugin.list_contents['Test List']['lines']]

    # will default to no selection
    assert la_plugin.selected_line == ''

    # check redshift
    assert la_plugin.selected_line_redshift == 0.0

    # but selecting a line from line-list (or clicking) should change the dropdown value
    # since sync is enabled by default
    assert la_plugin.sync_identify is True

    msg = LineIdentifyMessage(rest_names[1],
                              sender=specviz_helper)
    specviz_helper.app.session.hub.broadcast(msg)
    assert la_plugin.selected_line == rest_names[1]

    # and changing the dropdown should change the identified line
    la_plugin.selected_line = rest_names[0]
    assert ll_plugin.list_contents['Test List']['lines'][0].get('identify') is True
    assert ll_plugin.list_contents['Test List']['lines'][1].get('identify') is False

    # unless we disable the sync
    la_plugin.sync_identify = False
    la_plugin.selected_line = rest_names[1]
    assert ll_plugin.list_contents['Test List']['lines'][0].get('identify') is True
    assert ll_plugin.list_contents['Test List']['lines'][1].get('identify') is False

    # selected_line should become the same as identified_line
    assert la_plugin.selected_line == "Halpha 6563.0"
    assert la_plugin.identified_line == "O III 5007.0"
    la_plugin.sync_identify = True
    assert la_plugin.selected_line == "O III 5007.0"
    assert la_plugin.identified_line == "O III 5007.0"

    # identified_line should become the same as selected_line
    la_plugin.identified_line = ''
    la_plugin.sync_identify = False
    la_plugin.sync_identify = True
    assert la_plugin.identified_line == "O III 5007.0"

    # manually update redshift
    la_plugin.vue_line_assign()
    assert_allclose(la_plugin.results_centroid, 7307.4232674401555)
    line_mark = la_plugin.line_marks[la_plugin.line_items.index(la_plugin.selected_line)]
    assert_allclose(line_mark.rest_value, 5007)
    z = la_plugin._compute_redshift_for_selected_line()
    assert_allclose(z, (la_plugin.results_centroid - line_mark.rest_value)/line_mark.rest_value)
    assert_allclose(la_plugin.selected_line_redshift, z)


def test_coerce_unit():
    q_input = 1 * u.Unit('1E-20 erg m / (Angstrom cm**2 s)')
    q_input.uncertainty = 0.1 * u.Unit('1E-20 erg m / (Angstrom cm**2 s)')
    q_unit = u.Unit('erg / (cm**2 s)')
    q_coerced = _coerce_unit(q_input)
    assert_quantity_allclose(q_coerced, 1e-10 * q_unit)
    assert_quantity_allclose(q_coerced.uncertainty, 1e-11 * q_unit)
    q_input.uncertainty = None
    q_coerced = _coerce_unit(q_input)
    assert not hasattr(q_coerced, 'uncertainty')


def test_continuum_surrounding_spectral_subset(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), 2.153181e-13, atol=1e-15)


def test_continuum_spectral_same_value(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.width = 3

    # continuum and spectral cannot be the same value
    assert plugin.get_results()[0]['result'] == ''


def test_continuum_surrounding_invalid_width(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_width = 11
    assert plugin.get_results()[0]['result'] == ''


def test_continuum_subset_spectral_entire(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7400 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.spectral_subset_selected = 'Entire Spectrum'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), -2.79572e-13, atol=1e-15)


def test_continuum_subset_spectral_subset2(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6200 * unit,
                                                                        7000 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    specviz_helper.plugins['Subset Tools'].combination_mode = 'new'
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(7100 * unit,
                                                                        7700 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert plugin.spectral_subset.labels == ['Entire Spectrum', 'Subset 1', 'Subset 2']

    plugin.spectral_subset_selected = 'Subset 2'
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), 1.482418e-14, atol=1e-16)


def test_continuum_surrounding_no_right(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        8000 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), 4.204513e-14, atol=1e-16)


def test_continuum_surrounding_no_left(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6000 * unit,
                                                                        7500 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), 7.570859e-14, atol=1e-16)


def test_subset_changed(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    plugin.keep_active = True

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6000 * unit,
                                                                        7500 * unit))
    specviz_helper.app.state.drawer_content = 'plugins'

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6500 * unit,
                                                                        7500 * unit),
                                                         edit_subset='Subset 1')
    specviz_helper.app.state.drawer_content = 'plugins'

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.get_results()[0]['result']), 2.153181e-13, atol=1e-15)


def test_invalid_subset(specviz_helper, spectrum1d):
    # 6000-8000
    specviz_helper.load_data(spectrum1d, data_label="right_spectrum")

    # 5000-7000
    sp2 = Spectrum(spectral_axis=spectrum1d.spectral_axis - 1000*spectrum1d.spectral_axis.unit,
                   flux=spectrum1d.flux * 1.25)
    specviz_helper.load_data(sp2, data_label="left_spectrum")

    # apply subset that overlaps on left_spectrum, but not right_spectrum
    # NOTE: using a subset that overlaps the right_spectrum (reference) results in errors when
    # retrieving the subset (https://github.com/spacetelescope/jdaviz/issues/1868)
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(5000 * unit,
                                                                        6000 * unit))

    plugin = specviz_helper.plugins['Line Analysis']
    plugin.dataset = 'right_spectrum'
    assert plugin.dataset == 'right_spectrum'
    assert plugin.spectral_subset == 'Entire Spectrum'
    assert plugin._obj.spectral_subset_valid

    plugin.spectral_subset = 'Subset 1'
    assert not plugin._obj.spectral_subset_valid

    with pytest.raises(ValueError, match=r"spectral subset 'Subset 1' \(5000.0, 6000.0\) is outside data range of 'right_spectrum' \(6000.0, 8000.0\)"):  # noqa
        plugin.get_results()

    plugin.dataset = 'left_spectrum'
    assert plugin._obj.spectral_subset_valid
