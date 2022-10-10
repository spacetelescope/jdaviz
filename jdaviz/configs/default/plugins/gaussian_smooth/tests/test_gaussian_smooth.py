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

    gs = GaussianSmooth(app=app)
    gs.dataset_selected = 'test'
    gs.mode_selected = 'Spectral'
    gs.stddev = 3.2
    gs.add_to_viewer_selected = 'None'
    assert gs.results_label == 'spectral-smooth stddev-3.2'
    gs.vue_apply()
    # when not showing the results, the label will remain the same,
    # so there should be an overwrite warning
    assert gs.results_label_overwrite is True
    gs.add_to_viewer_selected = 'spectrum-viewer'
    gs.vue_apply()
    # but since we're overwriting, add_to_viewer_selected is ignored (and hidden in the UI)
    # so will still be hidden
    assert len(gs.dataset_items) == 1
    # by removing the data entry, the overwrite will no longer apply
    app.remove_data_from_viewer('spectrum-viewer', 'spectral-smooth stddev-3.2')
    app.data_collection.remove(app.data_collection['spectral-smooth stddev-3.2'])

    gs.add_to_viewer_selected = 'spectrum-viewer'
    gs.vue_apply()
    # since we now plotted the results, the dataset should be fixed,
    # but the dataset dropdown contains multiple choices, so the dataset
    # itself is prepended to the default label, and there is no longer
    # an overwrite warning.
    assert len(gs.dataset_items) == 2
    assert gs.dataset_selected == 'test'
    assert gs.results_label == 'test spectral-smooth stddev-3.2'
    assert gs.results_label_overwrite is False

    assert len(dc) == 2
    assert dc[1].label == 'spectral-smooth stddev-3.2'
    assert len(dc.external_links) == 3

    # Link cube 3D x, y, z to plugin 3D x, y, z

    # Link 2:
    # Pixel Axis 0 [z] from cube.pixel_component_ids[0]
    # Pixel Axis 0 [z] from plugin.pixel_component_ids[0]
    assert dc.external_links[0].cids1[0] == dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] == dc[-1].pixel_component_ids[0]

    # Link 3:
    # Pixel Axis 1 [y] from cube.pixel_component_ids[1]
    # Pixel Axis 1 [y] from plugin.pixel_component_ids[1]
    assert dc.external_links[1].cids1[0] == dc[0].pixel_component_ids[1]
    assert dc.external_links[1].cids2[0] == dc[-1].pixel_component_ids[1]

    # Link 4:
    # Pixel Axis 2 [x] from cube.pixel_component_ids[2]
    # Pixel Axis 2 [x] from plugin.pixel_component_ids[2]
    assert dc.external_links[2].cids1[0] == dc[0].pixel_component_ids[2]
    assert dc.external_links[2].cids2[0] == dc[-1].pixel_component_ids[2]


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_spatial_convolution(cubeviz_helper, spectrum1d_cube):
    dc = cubeviz_helper.app.data_collection
    cubeviz_helper.app.add_data(spectrum1d_cube, 'test')
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'test')

    gs = GaussianSmooth(app=cubeviz_helper.app)
    gs.dataset_selected = 'test'
    gs.mode_selected = 'Spatial'
    gs.stddev = 3
    assert gs.results_label == 'spatial-smooth stddev-3.0'
    gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == "spatial-smooth stddev-3.0"
    assert (dc["spatial-smooth stddev-3.0"].get_object(cls=Spectrum1D, statistic=None).shape
            == (4, 2, 2))
