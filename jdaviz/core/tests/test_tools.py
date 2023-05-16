import numpy as np
from numpy.testing import assert_allclose
from glue.core import Data


def test_boxzoom(cubeviz_helper, spectral_cube_wcs):
    data = Data(flux=np.ones((128, 128, 256)), label='Test Flux', coords=spectral_cube_wcs)
    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test Flux')

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')

    assert flux_viewer.state.y_min == -0.5
    assert flux_viewer.state.y_max == 127.5
    assert flux_viewer.state.x_min == -0.5
    assert flux_viewer.state.x_max == 127.5

    t = flux_viewer.toolbar.tools['jdaviz:boxzoom']
    t.activate()
    t.interact.selected_x = [10, 20]
    t.interact.selected_y = [20, 60]

    assert t.get_x_axis_with_aspect_ratio() == (-5., 35.)


def _get_lims(viewer):
    return [viewer.state.x_min, viewer.state.x_max,
            viewer.state.y_min, viewer.state.y_max]


def test_rangezoom(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label='test')

    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    assert_allclose(_get_lims(sv), [6000, 8000, 12.30618014327326, 16.542560043585965])

    t = sv.toolbar.tools['jdaviz:xrangezoom']
    t.activate()
    t.interact.selected = [6500, 7000]
    t.on_update_zoom()
    assert_allclose(_get_lims(sv), [6500, 7000, 12.30618014327326, 16.542560043585965])

    t = sv.toolbar.tools['jdaviz:yrangezoom']
    t.activate()
    t.interact.selected = [14, 15]
    t.on_update_zoom()
    assert_allclose(_get_lims(sv), [6500, 7000, 14, 15])
