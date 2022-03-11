import pytest
from jdaviz import Application
from specutils import Spectrum1D

from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth


def test_linking_after_spectral_smooth(spectrum1d_cube):

    app = Application(configuration="cubeviz")
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')

    gs = GaussianSmooth(app=app)

    gs._on_data_selected({'new': 'test'})
    gs.stddev = '3.2'
    gs.add_replace_results = False
    gs.vue_spectral_smooth()

    assert len(dc) == 2
    assert dc[1].label == 'Smoothed test stddev 3.2'
    assert len(dc.external_links) == 3

    assert dc.external_links[2].cids1[0] is dc[0].world_component_ids[0]
    assert dc.external_links[2].cids2[0] is dc[1].world_component_ids[0]


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_spatial_convolution(spectrum1d_cube):

    app = Application(configuration="cubeviz")
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')

    gs = GaussianSmooth(app=app)
    gs._on_data_selected({'new': 'test'})
    gs.stddev = '3'
    gs.vue_spatial_convolution()

    assert len(dc) == 2
    assert dc[1].label == "Smoothed test spatial stddev 3.0"
    assert (dc["Smoothed test spatial stddev 3.0"].get_object(cls=Spectrum1D, statistic=None).shape
            == (4, 2, 2))
