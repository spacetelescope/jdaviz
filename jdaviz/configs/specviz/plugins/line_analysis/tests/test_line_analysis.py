import astropy.units as u
from astropy.table import QTable
import numpy as np
from glue.core.roi import XRangeROI
from ipywidgets.widgets import widget_serialization

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
