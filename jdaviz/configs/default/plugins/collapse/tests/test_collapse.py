import numpy as np
import pytest
from astropy.nddata import CCDData
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


def test_save_collapsed_to_fits(cubeviz_helper, spectral_cube_wcs, tmp_path):

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

    # save output file with default name, make sure it exists
    collapse_plugin._obj.vue_save_as_fits()
    assert (tmp_path / fname).is_file()

    # read file back in, make sure it matches
    dat = CCDData.read(collapse_plugin._obj.filename)
    np.testing.assert_array_equal(dat.data, collapse_plugin._obj.collapsed_spec.data)
    assert dat.unit == collapse_plugin._obj.collapsed_spec.unit

    # make sure correct error message is raised when export_enabled is False
    # this won't appear in UI, but just to be safe.
    collapse_plugin._obj.export_enabled = False
    msg = "Writing out collapsed cube to file is currently disabled"
    with pytest.raises(ValueError, match=msg):
        collapse_plugin._obj.vue_save_as_fits()
    collapse_plugin._obj.export_enabled = True  # set back to True

    # check that trying to overwrite without overwrite=True sets overwrite_warn to True, to
    # display popup in UI
    assert collapse_plugin._obj.overwrite_warn is False
    collapse_plugin._obj.vue_save_as_fits()
    assert collapse_plugin._obj.overwrite_warn

    # check that writing out to a non existent directory fails as expected
    collapse_plugin._obj.filename = '/this/path/doesnt/exist.fits'
    with pytest.raises(ValueError, match="Invalid path=/this/path/doesnt"):
        collapse_plugin._obj.vue_save_as_fits()
    collapse_plugin._obj.filename == fname  # set back to original filename
