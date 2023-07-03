import os

import pytest
from astropy.io import fits
from astropy.nddata import CCDData
from astropy.wcs import WCS
from numpy.testing import assert_allclose

from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_moment_calculation(cubeviz_helper, spectrum1d_cube, tmpdir):
    dc = cubeviz_helper.app.data_collection
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)

    # Since we are not really displaying, need this to trigger GUI stuff.
    flux_viewer.shape = (100, 100)
    flux_viewer.state._set_axes_aspect_ratio(1)

    mm = MomentMap(app=cubeviz_helper.app)
    mm.dataset_selected = 'test[FLUX]'

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    assert mm.results_label == 'moment 0'

    mm.add_results.viewer.selected = cubeviz_helper._default_uncert_viewer_reference_name
    mm.vue_calculate_moment()

    assert mm.moment_available
    assert dc[1].label == 'moment 0'
    mv_data = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_uncert_viewer_reference_name
    ).data()
    # by default, will overwrite the previous entry (so only one data entry)
    assert len(mv_data) == 1
    assert mv_data[0].label == 'moment 0'

    assert len(dc.links) == 14

    # label should remain unchanged but raise overwrite warnings
    assert mm.results_label == 'moment 0'
    assert mm.results_label_overwrite is True

    # Make sure coordinate display works
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.state.slices == (0, 0, 1)
    # Slice 0 has 8 pixels, this is Slice 1
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value +8.00000e+00 Jy",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")

    # Make sure adding it to viewer does not crash.
    cubeviz_helper.app.add_data_to_viewer(
        cubeviz_helper._default_flux_viewer_reference_name, 'moment 0'
    )

    result = dc[1].get_object(cls=CCDData)
    assert result.shape == (4, 2)  # Cube shape is (2, 2, 4)
    assert isinstance(dc[1].coords, WCS)

    # Make sure coordinate display now show moment map info (no WCS)
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})

    # Slice 0 has 8 pixels, this is Slice 1  # noqa
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value +8.00000e+00 Jy",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")

    assert mm.filename == 'moment0_test_FLUX.fits'  # Auto-populated on calculate.
    mm.filename = str(tmpdir.join(mm.filename))  # But we want it in tmpdir for testing.
    mm.vue_save_as_fits()
    assert os.path.isfile(mm.filename)

    mm.n_moment = 1
    assert mm.results_label == 'moment 1'
    assert mm.results_label_overwrite is False
    mm.vue_calculate_moment()

    assert dc[2].label == 'moment 1'

    assert len(dc.links) == 22
    assert len(dc.external_links) == 2
    # Link 3D z to 2D x and 3D y to 2D y

    # Coordinate display should be unaffected.
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value +8.00000e+00 Jy",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_write_momentmap(cubeviz_helper, spectrum1d_cube, tmp_path):
    ''' Test writing a moment map out to a FITS file on disk '''

    # Simulate an existing file on disk to check for overwrite warning
    test_file = tmp_path / "test_file.fits"
    test_file_str = str(test_file)
    existing_sentinel_text = "This is a simulated, existing file on disk"
    test_file.write_text(existing_sentinel_text)

    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    plugin = cubeviz_helper.plugins['Moment Maps']
    moment = plugin.calculate_moment()

    # By default, we shouldn't be warning the user of anything
    assert plugin._obj.overwrite_warn is False

    # Attempt to write the moment map to the same file we created earlier.
    plugin._obj.filename = test_file_str
    plugin._obj.vue_save_as_fits()

    # We should get an overwrite warning
    assert plugin._obj.overwrite_warn is True
    # and shouldn't have written anything (the file should be intact)
    assert test_file.read_text() == existing_sentinel_text

    # Force overwrite the existing file
    plugin._obj.vue_overwrite_fits()

    # Read back in the file and check that it is equal to the one we calculated
    with fits.open(test_file_str) as pf:
        assert_allclose(pf[0].data, moment.data)
        w = WCS(pf[0].header)
        sky = w.pixel_to_world(0, 0)
        assert_allclose(sky.ra.deg, 204.9998877673)
        assert_allclose(sky.dec.deg, 27.0001)

    plugin._obj.filename = "fake_path/test_file.fits"
    with pytest.raises(ValueError, match="Invalid path"):
        plugin._obj.vue_save_as_fits()
