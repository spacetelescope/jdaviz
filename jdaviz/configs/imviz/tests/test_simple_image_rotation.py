import gwcs
import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS
from astropy.modeling import models
from astropy.nddata import NDData
from astropy.wcs import WCS
from gwcs import coordinate_frames as cf


def test_simple_image_rotation_plugin(imviz_helper):
    a = np.zeros((10, 8))

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

    # TODO: Test the plugin.
    # 0. Toggle it on
    # 1. Angle 0 should align N-up E-left, should have new WCS Data but hidden
    # 2. Try positive angle
    # 3. Add another viewer.
    # 4. Try negative angle on second viewer.
    # 5. Cross-test with Compass/Zoom-box, Line Profile, Coord Info?
    # 6. Untoggle and check state.
    # 7. Retoggle and check state.
    # 8. Make sure we also cover engine code not mentioned above but changed in the PR.

    # Second test function: Load just data without WCS, toggle on, should be no-op.

    # Also test function to make sure invalid angle does not crash plugin.
