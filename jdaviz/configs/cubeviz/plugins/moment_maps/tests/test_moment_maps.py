import numpy as np

from glue.core import Data

from jdaviz import Application
from ..moment_maps import MomentMap


def test_moment_calculation(spectral_cube_wcs):

    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    mm = MomentMap(app=app)

    mm.selected_data = 'test'
    mm.n_moment = 0
    mm.vue_calculate_moment(None)

    print(dc[1].get_object())

    assert mm.moment_available == True
    assert dc[1].label == 'Moment 0: test'
    assert dc[1].get_object().shape == (4,5)
