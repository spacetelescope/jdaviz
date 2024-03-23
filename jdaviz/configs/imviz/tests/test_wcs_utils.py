import gwcs
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import ICRS
from astropy.modeling import models
from astropy.wcs import WCS
from gwcs import coordinate_frames as cf
from numpy.testing import assert_allclose

from jdaviz.configs.imviz import wcs_utils
from jdaviz.configs.imviz.plugins.orientation.orientation import base_wcs_layer_label
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_GWCS, create_example_gwcs


def test_simple_fits_wcs():
    # CTYPE : ''  ''
    # CRVAL : 0.0  0.0
    # CRPIX : 0.0  0.0
    # PC1_1 PC1_2  : 1.0  0.0
    # PC2_1 PC2_2  : 0.0  1.0
    # CDELT : 1.0  1.0
    # NAXIS : 0  0
    w = WCS()
    result = wcs_utils.get_compass_info(w, (100, 100), r_fac=0.25)
    assert_allclose(result[:-1], (50, 50,
                                  50, 73.57533083557558,
                                  73.57809873817803, 47.53791379556649,
                                  0, 95.96136875946559))
    assert result[-1]

    # https://learn.astropy.org/tutorials/celestial_coords1.html
    w = WCS({'CTYPE1': 'RA---TAN',
             'CUNIT1': 'deg',
             'CDELT1': -0.0002777777778,
             'CRPIX1': 1,
             'CRVAL1': 337.5202808,
             'NAXIS1': 1024,
             'CTYPE2': 'DEC--TAN',
             'CUNIT2': 'deg',
             'CDELT2': 0.0002777777778,
             'CRPIX2': 1,
             'CRVAL2': -20.833333059999998,
             'NAXIS2': 1024})
    result = wcs_utils.get_compass_info(w, (1024, 1024), r_fac=0.25)
    assert_allclose(result[:-1], (512.0, 512.0,
                                  512.2415718047745, 767.9895741540789,
                                  255.98982015749573, 512.240013842715,
                                  0.054068767449065434, -90.00035302773995))
    assert not result[-1]


def test_hst_acs_flt_wcs():
    # jb5g05ubq_flt.fits -- has distortion
    w = WCS({'WCSAXES': 2,
             'CRPIX1': 2100.0,
             'CRPIX2': 1024.0,
             'PC1_1': -1.14852e-05,
             'PC1_2': 7.01477e-06,
             'PC2_1': 7.75765e-06,
             'PC2_2': 1.20927e-05,
             'CDELT1': 1.0,
             'CDELT2': 1.0,
             'CUNIT1': 'deg',
             'CUNIT2': 'deg',
             'CTYPE1': 'RA---TAN',
             'CTYPE2': 'DEC--TAN',
             'CRVAL1': 3.581704851882,
             'CRVAL2': -30.39197867265,
             'LONPOLE': 180.0,
             'LATPOLE': -30.39197867265,
             'MJDREF': 0.0,
             'RADESYS': 'ICRS'})
    result = wcs_utils.get_compass_info(w, (2048, 4096), r_fac=0.25)
    assert_allclose(result[:-1], (2048.0, 1024.0,
                                  2314.86981434716, 1460.9491537866957,
                                  1617.0522515837179, 1300.4560437373216,
                                  31.414796751823395, -88.73433642655598))
    assert not result[-1]


def test_simple_gwcs():
    # https://gwcs.readthedocs.io/en/latest/#getting-started
    shift_by_crpix = models.Shift(-(2048 - 1) * u.pix) & models.Shift(-(1024 - 1) * u.pix)
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
        5.63056810618 * u.deg, -72.05457184279 * u.deg, 180 * u.deg)
    det2sky = shift_by_crpix | rotation | tan | celestial_rotation
    det2sky.name = "linear_transform"
    detector_frame = cf.Frame2D(name="detector", axes_names=("x", "y"), unit=(u.pix, u.pix))
    sky_frame = cf.CelestialFrame(reference_frame=ICRS(), name='icrs', unit=(u.deg, u.deg))
    pipeline = [(detector_frame, det2sky), (sky_frame, None)]
    w = gwcs.wcs.WCS(pipeline)

    result = wcs_utils.get_compass_info(w, (1024, 2048), r_fac=0.25)
    assert_allclose(result[:-1], (1024.0, 512.0,
                                  1131.0265005852038, 279.446189124443,
                                  1262.0057201165127, 606.2863901330095,
                                  155.2870478938214, -86.89813081941797))
    assert not result[-1]


# TODO: Add more tests.
class TestWCSOnly(BaseImviz_WCS_GWCS):

    # TODO: Replace private API calls with more public ones when available.
    def test_non_wcs_layer_labels(self):
        self.imviz.link_data(link_type="wcs")
        assert len(self.imviz.app.data_collection) == 3

        # Confirm the WCS-only layer is created by WCS-linking .
        assert len(self.viewer.state.wcs_only_layers) == 1

        # Load a WCS-only layer, bypassing normal labeling scheme.
        ndd = wcs_utils._get_rotated_nddata_from_label(
            app=self.imviz.app,
            data_label="fits_wcs[DATA]",
            rotation_angle=5 * u.deg
        )
        self.imviz.load_data(ndd, data_label='ndd')
        assert self.imviz.app.data_collection[3].label == 'ndd'

        # Confirm that all data in collection are labeled.
        assert len(self.imviz.app.state.layer_icons) == 4  # 3 + 1

        # Confirm the new WCS-only layer is logged.
        assert len(self.viewer.state.wcs_only_layers) == 2

        # Load a second WCS-only layer.
        ndd2 = wcs_utils._get_rotated_nddata_from_label(
            app=self.imviz.app,
            data_label="fits_wcs[DATA]",
            rotation_angle=45 * u.deg
        )
        self.imviz.load_data(ndd2, data_label="rot: 45.00 deg")
        assert self.imviz.app.data_collection[4].label == "rot: 45.00 deg"

        # Confirm that all data in collection are labeled.
        assert len(self.imviz.app.data_collection) == 5  # 3 + 2
        assert len(self.imviz.app.state.layer_icons) == 5

        # Confirm the second WCS-only layer is logged
        assert len(self.viewer.state.wcs_only_layers) == 3

        # First entry is image data and the default reference data.
        assert self.imviz.app.state.layer_icons["fits_wcs[DATA]"] == "a"
        assert self.viewer.state.reference_data.label == base_wcs_layer_label


def test_get_rotated_nddata_from_label_no_wcs(imviz_helper):
    a = np.zeros((2, 2), dtype=np.int8)
    imviz_helper.load_data(a, data_label="no_wcs")
    with pytest.raises(ValueError, match=r".*has no WCS for rotation"):
        wcs_utils._get_rotated_nddata_from_label(imviz_helper.app, "no_wcs", 0 * u.deg)


def test_compute_scale():
    # NOTE: compute_scale does not work with FITS WCS.
    image_gwcs = create_example_gwcs((10, 10))
    fiducial = [197.8925, -1.36555556] * u.deg

    pixscale = wcs_utils.compute_scale(image_gwcs, fiducial, None)
    assert_allclose(pixscale, 3.0555555555555554e-05)

    pixscale = wcs_utils.compute_scale(image_gwcs, fiducial, None, pscale_ratio=1e+5)
    assert_allclose(pixscale, 3.0555555555555554)
