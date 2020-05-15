import numpy as np

from glue.core import Data
from glue.core.application_base import Application

from ..collapse import Collapse


def test_linking_after_collapse(spectral_cube_wcs):

    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    coll = Collapse(app=app)

    coll.selected_data_item = 'test'

    coll.selected_axis = 0
    coll.vue_collapse()

    assert len(dc) == 2
    assert dc[1].label == 'Collapsed test'
    assert len(dc.external_links) == 2

    assert dc.external_links[0].cids1[0] is dc[0].pixel_component_ids[1]
    assert dc.external_links[0].cids2[0] is dc[1].pixel_component_ids[0]
    assert dc.external_links[1].cids1[0] is dc[0].pixel_component_ids[2]
    assert dc.external_links[1].cids2[0] is dc[1].pixel_component_ids[1]

    coll.selected_axis = 1
    coll.vue_collapse()

    assert len(dc) == 2
    assert dc[1].label == 'Collapsed test'
    assert len(dc.external_links) == 2

    assert dc.external_links[0].cids1[0] is dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] is dc[1].pixel_component_ids[0]
    assert dc.external_links[1].cids1[0] is dc[0].pixel_component_ids[2]
    assert dc.external_links[1].cids2[0] is dc[1].pixel_component_ids[1]

    coll.selected_axis = 2
    coll.vue_collapse()

    assert len(dc) == 2
    assert dc[1].label == 'Collapsed test'
    assert len(dc.external_links) == 2

    assert dc.external_links[0].cids1[0] is dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] is dc[1].pixel_component_ids[0]
    assert dc.external_links[1].cids1[0] is dc[0].pixel_component_ids[1]
    assert dc.external_links[1].cids2[0] is dc[1].pixel_component_ids[1]
