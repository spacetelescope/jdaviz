import numpy as np

from jdaviz.core.marks import LineAnalysisContinuum


def test_open_plugin(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    specviz_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz_helper.app.state.tray_items]
    specviz_helper.app.state.tray_items_open = [tray_names.index('specviz-line-analysis')]

    # continuum should be created, plotted, and visible
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    continuum_marks = [m for m in sv.figure.marks if isinstance(m, LineAnalysisContinuum)]
    assert len(continuum_marks) == 3
    assert np.all([cm.visible for cm in continuum_marks])

    # closing tray/plugin should hide the continuum
    specviz_helper.app.state.drawer = False
    assert np.all([cm.visible is False for cm in continuum_marks])
