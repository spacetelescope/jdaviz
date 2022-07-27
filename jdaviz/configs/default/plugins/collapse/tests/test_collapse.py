import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum1D

from jdaviz.configs.default.plugins.collapse.collapse import Collapse


@pytest.mark.filterwarnings('ignore')
def test_linking_after_collapse(cubeviz_helper, spectral_cube_wcs):
    cubeviz_helper.load_data(Spectrum1D(flux=np.ones((3, 4, 5)) * u.nJy, wcs=spectral_cube_wcs))
    dc = cubeviz_helper.app.data_collection

    coll = Collapse(app=cubeviz_helper.app)

    coll.selected_data_item = 'Unknown spectrum object[FLUX]'
    coll.dataset_selected = 'Unknown spectrum object[FLUX]'

    assert coll.results_label == 'collapsed'
    coll.vue_collapse()
    assert coll.results_label_overwrite is True

    assert len(dc) == 2
    assert dc[1].label == 'collapsed'
    assert len(dc.external_links) == 2

    # Link 3D z to 2D x and 3D y to 2D y

    # Link 1:
    # Pixel Axis 0 [z] from cube.pixel_component_ids[0]
    # Pixel Axis 1 [x] from plugin.pixel_component_ids[1]
    assert dc.external_links[0].cids1[0] == dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] == dc[-1].pixel_component_ids[1]
    # Link 2:
    # Pixel Axis 1 [y] from cube.pixel_component_ids[1]
    # Pixel Axis 0 [y] from plugin.pixel_component_ids[0]
    assert dc.external_links[1].cids1[0] == dc[0].pixel_component_ids[1]
    assert dc.external_links[1].cids2[0] == dc[-1].pixel_component_ids[0]
