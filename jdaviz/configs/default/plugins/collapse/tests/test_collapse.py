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

    coll.add_replace_results = False
    coll.vue_collapse()

    assert len(dc) == 2
    assert dc[1].label == 'Collapsed 1 Unknown spectrum object[FLUX]'
    assert len(dc.external_links) == 2

    assert dc.external_links[1].cids1[0] is dc[1].pixel_component_ids[0]
    assert dc.external_links[1].cids2[0] is dc[0].pixel_component_ids[1]
