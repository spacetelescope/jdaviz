import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum1D


@pytest.mark.filterwarnings('ignore')
def test_linking_after_collapse(cubeviz_helper, spectral_cube_wcs):
    cubeviz_helper.load_data(Spectrum1D(flux=np.ones((3, 4, 5)) * u.nJy, wcs=spectral_cube_wcs))
    dc = cubeviz_helper.app.data_collection

    # TODO: this now fails when instantiating Collapse after initialization
    coll = cubeviz_helper.plugins['Collapse']._obj

    coll.selected_data_item = 'Unknown spectrum object[FLUX]'
    coll.dataset_selected = 'Unknown spectrum object[FLUX]'

    assert coll.results_label == 'collapsed'
    coll.vue_collapse()
    assert coll.results_label_overwrite is True

    assert len(dc) == 3
    assert dc[2].label == 'collapsed'
    assert len(dc.external_links) == 4

    # Link 3D z to 2D x and 3D y to 2D y

    # Link 1:
    # Pixel Axis 0 [z] from cube.pixel_component_ids[0]
    # Pixel Axis 1 [x] from plugin.pixel_component_ids[1]
    assert dc.external_links[2].cids1[0] == dc[0].pixel_component_ids[0]
    assert dc.external_links[2].cids2[0] == dc[-1].pixel_component_ids[1]
    # Link 2:
    # Pixel Axis 1 [y] from cube.pixel_component_ids[1]
    # Pixel Axis 0 [y] from plugin.pixel_component_ids[0]
    assert dc.external_links[3].cids1[0] == dc[0].pixel_component_ids[1]
    assert dc.external_links[3].cids2[0] == dc[-1].pixel_component_ids[0]


def test_collapsed_to_extract_plugin(cubeviz_helper, spectral_cube_wcs, tmp_path):

    cubeviz_helper.load_data(Spectrum1D(flux=np.ones((3, 4, 5)) * u.nJy, wcs=spectral_cube_wcs))

    collapse_plugin = cubeviz_helper.plugins['Collapse']

    # make sure export enabled is true, and that before the collapse function
    # is run `collapsed_spec_available` is correctly set to False
    assert collapse_plugin._obj.export_enabled
    assert collapse_plugin._obj.collapsed_spec_available is False

    # run collapse function, and make sure `collapsed_spec_available` was set to True
    collapse_plugin._obj.vue_collapse()
    assert collapse_plugin._obj.collapsed_spec_available

    # check that default filename is correct, then change path
    fname = 'collapsed_sum_Unknown spectrum object_FLUX.fits'
    assert collapse_plugin._obj.filename == fname
    collapse_plugin._obj.filename = str(tmp_path / fname)

    label = collapse_plugin._obj.add_results.label
    export_plugin = cubeviz_helper.plugins['Export']._obj

    assert label in export_plugin.data_collection.labels
