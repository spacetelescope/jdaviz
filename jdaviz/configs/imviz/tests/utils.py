import gwcs
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import ICRS
from astropy.io import fits
from astropy.modeling import models
from astropy.nddata import NDData
from astropy.wcs import WCS
from gwcs import coordinate_frames as cf, wcs as gwcs_wcs

__all__ = ['BaseImviz_WCS_NoWCS', 'BaseImviz_WCS_WCS', 'BaseImviz_WCS_GWCS', 'BaseImviz_GWCS_GWCS']


class BaseImviz_WCS_NoWCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        hdu = fits.ImageHDU(np.arange(100).reshape((10, 10)), name='SCI')

        # Apply some celestial WCS from
        # https://learn.astropy.org/rst-tutorials/celestial_coords1.html
        hdu.header.update({'CTYPE1': 'RA---TAN',
                           'CUNIT1': 'deg',
                           'CDELT1': -0.0002777777778,
                           'CRPIX1': 1,
                           'CRVAL1': 337.5202808,
                           'NAXIS1': 10,
                           'CTYPE2': 'DEC--TAN',
                           'CUNIT2': 'deg',
                           'CDELT2': 0.0002777777778,
                           'CRPIX2': 1,
                           'CRVAL2': -20.833333059999998,
                           'NAXIS2': 10})

        # Data with WCS
        imviz_helper.load_data(hdu, data_label='has_wcs')

        # Data without WCS
        imviz_helper.load_data(hdu, data_label='no_wcs')
        imviz_helper.app.data_collection[1].coords = None

        self.wcs = WCS(hdu.header)
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer._obj
        self.subset_plugin = self.imviz.plugins['Subset Tools']

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)


class BaseImviz_WCS_WCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        arr = np.ones((10, 10))

        # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
        hdu1 = fits.ImageHDU(arr, name='SCI')
        hdu1.header.update({'CTYPE1': 'RA---TAN',
                            'CUNIT1': 'deg',
                            'CDELT1': -0.0002777777778,
                            'CRPIX1': 1,
                            'CRVAL1': 337.5202808,
                            'NAXIS1': 10,
                            'CTYPE2': 'DEC--TAN',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.0002777777778,
                            'CRPIX2': 1,
                            'CRVAL2': -20.833333059999998,
                            'NAXIS2': 10})
        imviz_helper.load_data(hdu1, data_label='has_wcs_1')

        # Second data with WCS, similar to above but dithered by 1 pixel in X.
        hdu2 = fits.ImageHDU(arr, name='SCI')
        hdu2.header.update({'CTYPE1': 'RA---TAN',
                            'CUNIT1': 'deg',
                            'CDELT1': -0.0002777777778,
                            'CRPIX1': 2,
                            'CRVAL1': 337.5202808,
                            'NAXIS1': 10,
                            'CTYPE2': 'DEC--TAN',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.0002777777778,
                            'CRPIX2': 1,
                            'CRVAL2': -20.833333059999998,
                            'NAXIS2': 10})
        imviz_helper.load_data(hdu2, data_label='has_wcs_2')

        self.wcs_1 = WCS(hdu1.header)
        self.wcs_2 = WCS(hdu2.header)
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer._obj

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)


class BaseImviz_WCS_GWCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        arr = np.zeros((10, 8))  # (ny, nx)
        arr[0, 0] = 1  # Bright corner for sanity check

        # FITS WCS that is adapted from HST/ACS without the distortion.
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

        # GWCS that is adapted from its Getting Started.
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
        w_gwcs.bounding_box = ((0, 8), (0, 10)) * u.pix  # x, y

        # Load data into Imviz:
        # 1. Data with FITS WCS and unit.
        # 2. Data with GWCS (rotated w.r.t. FITS WCS) and no unit.
        imviz_helper.load_data(NDData(arr, wcs=w_fits, unit='electron/s'), data_label='fits_wcs')
        imviz_helper.load_data(NDData(arr, wcs=w_gwcs), data_label='gwcs')

        self.wcs_1 = w_fits
        self.wcs_2 = w_gwcs
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer._obj

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)


class BaseImviz_GWCS_GWCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        arr = np.zeros((10, 8))  # (ny, nx)
        arr[0, 0] = 1  # Bright corner for sanity check

        # GWCS that is adapted from its Getting Started.
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
        w_gwcs_1 = gwcs.WCS(pipeline)
        w_gwcs_1.bounding_box = ((0, 8), (0, 10)) * u.pix  # x, y

        # Second GWCS that is offset
        shift_by_crpix = models.Shift(-1 * u.pix) & models.Shift(-1 * u.pix)
        det2sky = shift_by_crpix | rotation | tan | celestial_rotation
        det2sky.name = "linear_transform"
        pipeline = [(detector_frame, det2sky), (sky_frame, None)]
        w_gwcs_2 = gwcs.WCS(pipeline)
        w_gwcs_2.bounding_box = ((0, 8), (0, 10)) * u.pix  # x, y

        # Load data into Imviz
        imviz_helper.load_data(NDData(arr, wcs=w_gwcs_1, unit='electron/s'), data_label='gwcs1')
        imviz_helper.load_data(NDData(arr, wcs=w_gwcs_2), data_label='gwcs2')

        self.wcs_1 = w_gwcs_1
        self.wcs_2 = w_gwcs_2
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer._obj

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)


# --- This was used to generate data/roman_wfi_image_model.asdf ---

def create_example_gwcs(shape):
    # Example adapted from photutils:
    #   https://github.com/astropy/photutils/blob/
    #   2825356f1d876cacefb3a03d104a4c563065375f/photutils/datasets/make.py#L821
    rho = np.pi / 3.0
    # Roman plate scale:
    scale = (0.11 * (u.arcsec / u.pixel)).to_value(u.deg / u.pixel)

    shift_by_crpix = (models.Shift((-shape[1] / 2) + 1)
                      & models.Shift((-shape[0] / 2) + 1))

    cd_matrix = np.array([[-scale * np.cos(rho), scale * np.sin(rho)],
                          [scale * np.sin(rho), scale * np.cos(rho)]])

    rotation = models.AffineTransformation2D(cd_matrix, translation=[0, 0])
    rotation.inverse = models.AffineTransformation2D(
        np.linalg.inv(cd_matrix), translation=[0, 0])

    tan = models.Pix2Sky_TAN()
    celestial_rotation = models.RotateNative2Celestial(197.8925, -1.36555556, 180.0)

    det2sky = shift_by_crpix | rotation | tan | celestial_rotation
    det2sky.name = 'linear_transform'

    detector_frame = cf.Frame2D(name='detector', axes_names=('x', 'y'), unit=(u.pix, u.pix))

    sky_frame = cf.CelestialFrame(reference_frame=ICRS(), name='icrs', unit=(u.deg, u.deg))

    pipeline = [(detector_frame, det2sky), (sky_frame, None)]
    wcs = gwcs_wcs.WCS(pipeline)
    wcs.bounding_box = [(0, shape[0]), (0, shape[1])]
    return wcs


def create_wfi_image_model(image_shape=(20, 10), **kwargs):
    """
    Create a dummy Roman WFI ImageModel instance with valid values
    for attributes required by the schema.

    Requires roman_datamodels >= 0.14.2

    Parameters
    ----------
    image_shape : tuple
        Shape of the synthetic image to produce.

    **kwargs
        Additional or overridden attributes.

    Returns
    -------
    data_model : `roman_datamodels.datamodel.ImageModel`

    """  # noqa: E501
    from roman_datamodels import datamodels as rdd
    from roman_datamodels.maker_utils import mk_level2_image

    wfi_image = mk_level2_image(shape=image_shape, **kwargs)

    # introduce synthetic gwcs:
    wfi_image["meta"]["wcs"] = create_example_gwcs(image_shape)

    return rdd.ImageModel(wfi_image)
