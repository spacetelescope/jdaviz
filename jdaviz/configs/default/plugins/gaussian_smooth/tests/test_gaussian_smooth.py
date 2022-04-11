import pytest
from jdaviz import Application
from specutils import Spectrum1D

from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth


def test_linking_after_spectral_smooth(spectrum1d_cube):

    app = Application(configuration="cubeviz")
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer('flux-viewer', 'test')

    assert len(dc) == 1
    assert len(dc.external_links) == 0

    gs = GaussianSmooth(app=app)
    gs.dataset_selected = 'test'
    gs.selected_mode = 'Spectral'
    gs.stddev = 3.2
    assert gs.results_label == 'spectral-smooth stddev-3.2'
    gs.vue_apply()
    assert gs.results_label_overwrite is True

    assert len(dc) == 2
    assert dc[1].label == 'spectral-smooth stddev-3.2'
    assert len(dc.external_links) == 3

    assert dc.external_links[2].cids1[0] is dc[0].world_component_ids[0]
    assert dc.external_links[2].cids2[0] is dc[1].world_component_ids[0]


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_spatial_convolution(spectrum1d_cube):

    app = Application(configuration="cubeviz")
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer('flux-viewer', 'test')

    gs = GaussianSmooth(app=app)
    gs.dataset_selected = 'test'
    gs.selected_mode = 'Spatial'
    gs.stddev = 3
    assert gs.results_label == 'spatial-smooth stddev-3.0'
    gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == "spatial-smooth stddev-3.0"
    assert (dc["spatial-smooth stddev-3.0"].get_object(cls=Spectrum1D, statistic=None).shape
            == (4, 2, 2))
