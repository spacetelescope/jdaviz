import gwcs
import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS
from astropy.modeling import models
from astropy.nddata import NDData
from astropy.wcs import WCS
from gwcs import coordinate_frames as cf
from numpy.testing import assert_allclose


def test_simple_image_rotation_plugin(imviz_helper):
    # Mimic interactive mode where viewer is displayed.
    imviz_helper.default_viewer.shape = (100, 100)
    imviz_helper.default_viewer.state._set_axes_aspect_ratio(1)

    a = np.zeros((10, 8))
    a[0, 0] = 1  # Bright corner for sanity check.

    # Adapted from HST/ACS FITS WCS without the distortion.
    w_fits = WCS({'WCSAXES': 2, 'NAXIS1': 8, 'NAXIS2': 10,
                  'CRPIX1': 5.0, 'CRPIX2': 5.0,
                  'PC1_1': -1.14852e-05, 'PC1_2': 7.01477e-06,
                  'PC2_1': 7.75765e-06, 'PC2_2': 1.20927e-05,
                  'CDELT1': 1.0, 'CDELT2': 1.0,
                  'CUNIT1': 'deg', 'CUNIT2': 'deg',
                  'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN',
                  'CRVAL1': 3.581704851882, 'CRVAL2': -30.39197867265,
                  'LONPOLE': 180.0, 'LATPOLE': -30.39197867265,
                  'MJDREF': 0.0, 'RADESYS': 'ICRS'})

    # Adapted from GWCS example.
    shift_by_crpix = models.Shift(-(5 - 1) * u.pix) & models.Shift(-(5 - 1) * u.pix)
    matrix = np.array([[1.290551569736E-05, 5.9525007864732E-06],
                       [5.0226382102765E-06, -1.2644844123757E-05]])
    rotation = models.AffineTransformation2D(matrix * u.deg, translation=[0, 0] * u.deg)
    rotation.input_units_equivalencies = {"x": u.pixel_scale(1 * (u.deg / u.pix)),
                                          "y": u.pixel_scale(1 * (u.deg / u.pix))}
    rotation.inverse = models.AffineTransformation2D(np.linalg.inv(matrix) * u.pix,
                                                     translation=[0, 0] * u.pix)
    rotation.inverse.input_units_equivalencies = {"x": u.pixel_scale(1 * (u.pix / u.deg)),
                                                  "y": u.pixel_scale(1 * (u.pix / u.deg))}
    tan = models.Pix2Sky_TAN()
    celestial_rotation = models.RotateNative2Celestial(
        3.581704851882 * u.deg, -30.39197867265 * u.deg, 180 * u.deg)
    det2sky = shift_by_crpix | rotation | tan | celestial_rotation
    det2sky.name = "linear_transform"
    detector_frame = cf.Frame2D(name="detector", axes_names=("x", "y"), unit=(u.pix, u.pix))
    sky_frame = cf.CelestialFrame(reference_frame=ICRS(), name='icrs', unit=(u.deg, u.deg))
    pipeline = [(detector_frame, det2sky), (sky_frame, None)]
    w_gwcs = gwcs.WCS(pipeline)

    # Load data into Imviz.
    imviz_helper.load_data(NDData(a, wcs=w_fits, unit='electron/s'), data_label='fits_wcs')
    imviz_helper.load_data(NDData(a, wcs=w_gwcs), data_label='gwcs')
    imviz_helper.load_data(a, data_label='no_wcs')

    plg = imviz_helper.app.get_tray_item_from_name('imviz-rotate-image')
    plg.plugin_opened = True

    # Toggle it on.
    plg.rotate_mode_on = True
    assert plg.dataset.selected == 'fits_wcs[DATA]'

    # Rotate with default settings.
    plg.vue_rotate_image()
    assert_allclose(plg._theta, 0)

    # Dummy data with desired WCS is now in data collection but user cannot see it.
    assert imviz_helper.app.data_collection.labels == [
        'fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs', '_simple_rotated_wcs_ref[DATA]']
    assert plg.dataset.labels == ['fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs']

    # The zoom box is now a rotated rombus.
    # no_wcs is the same as fits_wcs because they are linked by pixel, but gwcs is different.
    fits_wcs_zoom_limits = imviz_helper.default_viewer._get_zoom_limits(
        imviz_helper.app.data_collection['fits_wcs[DATA]'])
    assert_allclose(fits_wcs_zoom_limits, ((-0.37873422, 5.62910616), (3.42315751, 11.85389963),
                                           (13.52329142, 5.37451188), (9.72139968, -0.85028158)))
    assert_allclose(fits_wcs_zoom_limits, imviz_helper.default_viewer._get_zoom_limits(
        imviz_helper.app.data_collection['no_wcs']))
    assert_allclose(imviz_helper.default_viewer._get_zoom_limits('gwcs[DATA]'), (
        (7.60196643, 6.55912761), (10.83179746, -0.44341285),
        (0.25848145, -4.64322363), (-2.97134959, 2.35931683)))

    # TODO: Test the plugin.
    # 2. Try positive angle
    # 3. Add another viewer.
    # 4. Try negative angle on second viewer.
    # 5. Cross-test with Compass/Zoom-box, Line Profile, Coord Info?
    # 6. Untoggle and check state.
    # 7. Retoggle and check state.
    # 8. Make sure we also cover engine code not mentioned above but changed in the PR.

    # Second test function: Load just data without WCS, toggle on, should be no-op.

    # Also test function to make sure invalid angle does not crash plugin.
