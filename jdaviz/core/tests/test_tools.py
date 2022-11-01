import numpy as np
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
