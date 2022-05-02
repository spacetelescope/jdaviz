import astropy.units as u
from astropy.table import QTable
import numpy as np
from glue.core.roi import XRangeROI
from glue.core.edit_subset_mode import NewMode
from ipywidgets.widgets import widget_serialization

from jdaviz.configs.specviz.plugins.line_analysis.line_analysis import _coerce_unit
from jdaviz.core.events import LineIdentifyMessage
from jdaviz.core.marks import LineAnalysisContinuum


def test_plugin(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # closing tray/plugin should hide the continuum
    specviz_helper.app.state.drawer = False
    assert np.all([cm.visible is False for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 7400))
    specviz_helper.app.state.drawer = True

    ipy_model_id = specviz_helper.app.state.tray_items[plugin_index]['widget']
    plugin = widget_serialization['from_json'](ipy_model_id, None)
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.selected_subset = 'Subset 1'
    plugin.selected_continuum = 'Surrounding'
    plugin.width = 3

    for result_dict in plugin.results:
        if result_dict in ['Line Flux']:
            # should have an assigned uncertainty (with min required version of specutils)
            assert len(result_dict.get('uncertainty')) > 0


def test_line_identify(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
    lt['listname'] = 'Test List'
    specviz_helper.load_line_list(lt)

    ll_plugin = specviz_helper.app.get_tray_item_from_name('g-line-list')
    la_plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    rest_names = [line['name_rest'] for line in ll_plugin.list_contents['Test List']['lines']]

    # will default to no selection
    assert la_plugin.selected_line == ''

    # check redshift
    assert la_plugin.selected_line_redshift == 0.0

    # but selecting a line from line-list (or clicking) should change the dropdown value
    # since sync is enabled by default
    assert la_plugin.sync_identify is True
    # think this is the problem and we need to send the rest name here!
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
    assert la_plugin.selected_line_redshift == -1.0


def test_coerce_unit():
    q_input = 1 * u.Unit('1E-20 erg m / (Angstrom cm**2 s)')
    q_input.uncertainty = 0.1 * u.Unit('1E-20 erg m / (Angstrom cm**2 s)')
    q_coerced = _coerce_unit(q_input)
    assert q_coerced.unit == u.Unit('erg / (cm**2 s)')
    assert np.allclose(q_coerced.value, 1e-20 * u.m.to(u.Angstrom))
    assert q_coerced.uncertainty.unit == u.Unit('erg / (cm**2 s)')
    assert np.allclose(q_coerced.uncertainty.value, 0.1 * 1e-20 * u.m.to(u.Angstrom))
    q_input.uncertainty = None
    q_coerced = _coerce_unit(q_input)
    assert not hasattr(q_coerced, 'uncertainty')


def test_continuum_surrounding_spectral_subset(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 7400))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), 350.89288537581467, atol=1e-5)


def test_continuum_spectral_same_value(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 7400))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.width = 3

    # continuum and spectral cannot be the same value
    assert plugin.results[0]['result'] == ''


def test_continuum_surrounding_invalid_width(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 7400))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.spectral_subset_selected = 'Subset 1'
    plugin.width = 11
    assert plugin.results[0]['result'] == ''


def test_continuum_subset_spectral_entire(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 7400))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.spectral_subset_selected = 'Entire Spectrum'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), -467.6854635447396, atol=1e-5)


def test_continuum_subset_spectral_subset2(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6200, 7000))
    specviz_helper.app.state.drawer = True

    sv.session.edit_subset_mode._mode = NewMode
    sv.session.edit_subset = []
    sv.apply_roi(XRangeROI(7100, 7700))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert plugin.spectral_subset.labels == ['Entire Spectrum', 'Subset 1', 'Subset 2']

    plugin.spectral_subset_selected = 'Subset 2'
    plugin.continuum_subset_selected = 'Subset 1'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), 32.520521, atol=1e-5)


def test_continuum_surrounding_no_right(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6500, 8000))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), 39.76685499263615, atol=1e-5)


def test_continuum_surrounding_no_left(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6000, 7500))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), 146.67186446784513, atol=1e-5)


def test_subset_changed(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    plugin_index = tray_names.index('specviz-line-analysis')
    specviz_helper.app.state.tray_items_open = [plugin_index]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # add a region and rerun stats for that region
    sv.apply_roi(XRangeROI(6000, 7500))
    specviz_helper.app.state.drawer = True

    plugin = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert 'Subset 1' in plugin.spectral_subset.labels

    plugin.spectral_subset_selected = 'Subset 1'
    plugin.continuum_subset_selected = 'Surrounding'
    plugin.width = 3

    sv.apply_roi(XRangeROI(6500, 7500))
    specviz_helper.app.state.drawer = True

    # Values have not yet been validated
    np.testing.assert_allclose(float(plugin.results[0]['result']), 350.89288537581467, atol=1e-5)
