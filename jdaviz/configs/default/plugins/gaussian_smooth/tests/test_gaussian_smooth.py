import numpy as np

from glue.core import Data
from glue.core.application_base import Application

from ..gaussian_smooth import GaussianSmooth


def test_linking_after_gaussian_smooth(spectral_cube_wcs):

    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    coll = GaussianSmooth(app=app)

    coll.vue_data_selected('test')
    coll.stddev = '3.2'
    coll.vue_gaussian_smooth()

    assert len(dc) == 2
    assert dc[1].label == 'Smoothed test'
    assert len(dc.external_links) == 1

    assert dc.external_links[0].cids1[0] is dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] is dc[1].pixel_component_ids[0]
