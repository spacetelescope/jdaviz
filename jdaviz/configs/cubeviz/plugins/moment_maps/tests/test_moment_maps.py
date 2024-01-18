import os
import warnings
from pathlib import Path

import pytest
from astropy.io import fits
from astropy.nddata import CCDData
from astropy.wcs import WCS
from astroquery.mast import Observations
from numpy.testing import assert_allclose


def test_user_api(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    mm = cubeviz_helper.plugins['Moment Maps']
    assert not mm._obj.continuum_marks['center'].visible
    with mm.as_active():
        assert mm._obj.continuum_marks['center'].visible
        mm.n_moment = 0
        # no continuum so marks should be empty
        assert len(mm._obj.continuum_marks['center'].x) == 0

        mom = mm.calculate_moment()

        mm.continuum = 'Surrounding'
        mm.continuum_width = 10
        assert len(mm._obj.continuum_marks['center'].x) > 0

        mom_sub = mm.calculate_moment()
        assert isinstance(mom_sub.wcs, WCS)

        assert mom != mom_sub

        mm.n_moment = -1
        with pytest.raises(ValueError, match="Moment must be a positive integer"):
            mm.calculate_moment()

        mm.n_moment = 1
        with pytest.raises(ValueError, match="not one of"):
            mm._obj.output_unit_selected = "Bad Unit"
        mm._obj.output_unit_selected = "Flux"
        with pytest.raises(ValueError, match="units must be in"):
            mm.calculate_moment()


def test_moment_calculation(cubeviz_helper, spectrum1d_cube, tmp_path):
    dc = cubeviz_helper.app.data_collection
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)

    # Since we are not really displaying, need this to trigger GUI stuff.
    flux_viewer.shape = (100, 100)
    flux_viewer.state._set_axes_aspect_ratio(1)

    mm = cubeviz_helper.plugins["Moment Maps"]
    mm.dataset = 'test[FLUX]'

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    assert mm._obj.results_label == 'moment 0'
    assert mm.output_unit == "Flux"

    mm._obj.add_results.viewer.selected = cubeviz_helper._default_uncert_viewer_reference_name
    mm._obj.vue_calculate_moment()

    assert mm._obj.moment_available
    assert dc[1].label == 'moment 0'
    mv_data = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_uncert_viewer_reference_name
    ).data()
    # by default, will overwrite the previous entry (so only one data entry)
    assert len(mv_data) == 1
    assert mv_data[0].label == 'moment 0'

    assert len(dc.links) == 14

    # label should remain unchanged but raise overwrite warnings
    assert mm._obj.results_label == 'moment 0'
    assert mm._obj.results_label_overwrite is True

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

    assert mm._obj.filename == 'moment0_test_FLUX.fits'  # Auto-populated on calculate.
    mm._obj.filename = str(tmp_path / mm._obj.filename)  # But we want it in tmp_path for testing.
    mm._obj.vue_save_as_fits()
    assert os.path.isfile(mm._obj.filename)

    mm._obj.n_moment = 1
    mm._obj.output_unit_selected = "Spectral Unit"
    assert mm._obj.results_label == 'moment 1'
    assert mm._obj.results_label_overwrite is False
    mm._obj.vue_calculate_moment()

    assert dc[2].label == 'moment 1'

    assert len(dc.links) == 22
    assert len(dc.external_links) == 4  # pixel linked
    # Link 3D z to 2D x and 3D y to 2D y

    # Coordinate display should be unaffected.
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value +8.00000e+00 Jy",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")


def test_moment_velocity_calculation(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    uncert_viewer = cubeviz_helper.app.get_viewer("uncert-viewer")

    # Since we are not really displaying, need this to trigger GUI stuff.
    uncert_viewer.shape = (100, 100)
    uncert_viewer.state._set_axes_aspect_ratio(1)

    mm = cubeviz_helper.plugins["Moment Maps"]
    print(mm._obj.dataset_selected)
    mm._obj.dataset_selected = 'test[FLUX]'

    # Test moment 1 in velocity
    mm.n_moment = 1
    mm.add_results.viewer = "uncert-viewer"
    assert mm._obj.results_label == 'moment 1'
    mm.output_unit = "Velocity"

    with pytest.raises(ValueError, match="reference_wavelength must be set"):
        mm.calculate_moment()

    mm.reference_wavelength = 4.63e-7
    mm.calculate_moment()

    # Make sure coordinate display works
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(uncert_viewer, {'event': 'mousemove',
                                                        'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value -4.14668e+02 km / s",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")

    # Test moment 2 in velocity
    mm.n_moment = 2
    mm.calculate_moment()

    label_mouseover._viewer_mouse_event(uncert_viewer, {'event': 'mousemove',
                                                        'domain': {'x': 1, 'y': 1}})

    assert label_mouseover.as_text() == ("Pixel x=01.0 y=01.0 Value +2.32415e+01 km / s",
                                         "World 13h39m59.9461s +27d00m00.7200s (ICRS)",
                                         "204.9997755344 27.0001999998 (deg)")


def test_write_momentmap(cubeviz_helper, spectrum1d_cube, tmp_path):
    ''' Test writing a moment map out to a FITS file on disk '''

    # Simulate an existing file on disk to check for overwrite warning
    test_file = tmp_path / "test_file.fits"
    test_file_str = str(test_file)
    existing_sentinel_text = "This is a simulated, existing file on disk"
    test_file.write_text(existing_sentinel_text)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
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


@pytest.mark.remote_data
def test_momentmap_nirspec_prism(cubeviz_helper, tmp_path):
    uri = "mast:jwst/product/jw02732-o003_t002_nirspec_prism-clear_s3d.fits"
    download_path = str(tmp_path / Path(uri).name)
    Observations.download_file(uri, local_path=download_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cubeviz_helper.load_data(download_path)
    plugin = cubeviz_helper.plugins['Moment Maps']
    plugin.calculate_moment()
    assert isinstance(plugin._obj.moment.wcs, WCS)

    # Because cube axes order is re-arranged by specutils on load, this gets confusing.
    # There is a swapaxes within Moment Map WCS calculation.
    sky_moment = plugin._obj.moment.wcs.pixel_to_world(50, 30)
    sky_cube = cubeviz_helper.app.data_collection[0].meta["_orig_spec"].wcs.celestial.pixel_to_world(30, 50)  # noqa: E501
    assert_allclose((sky_moment.ra.deg, sky_moment.dec.deg),
                    (sky_cube.ra.deg, sky_cube.dec.deg))
