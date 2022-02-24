import numpy as np
from glue.core.roi import XRangeROI
from ipywidgets.widgets import widget_serialization

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
    assert 'Subset 1' in plugin.spectral_subset_items
    plugin.selected_subset = 'Subset 1'
    plugin.selected_continuum = 'Surrounding'
    plugin.width = 3
