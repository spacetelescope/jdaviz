import numpy as np

from glue.core import Data
from jdaviz import Application
from spectral_cube import SpectralCube

from ..gaussian_smooth import GaussianSmooth


def test_linking_after_spectral_smooth(spectral_cube_wcs):

    app = Application(configuration="cubeviz")
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    gs = GaussianSmooth(app=app)

    gs._on_data_selected({'new': 'test'})
    gs.stddev = '3.2'
    gs.vue_spectral_smooth()

    assert len(dc) == 2
    assert dc[1].label == 'Smoothed test stddev 3.2'
    assert len(dc.external_links) == 1

    assert dc.external_links[0].cids1[0] is dc[0].world_component_ids[0]
    assert dc.external_links[0].cids2[0] is dc[1].world_component_ids[0]


def test_spatial_convolution(spectral_cube_wcs):

    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    gs = GaussianSmooth(app=app)
    gs._on_data_selected({'new': 'test'})
    gs.stddev = '3'
    gs.vue_spatial_convolution()

    assert len(dc) == 2
    assert dc[1].label == "Smoothed test spatial stddev 3.0"
    assert dc["Smoothed test spatial stddev 3.0"].get_object(cls=SpectralCube).shape == (3, 4, 5)
