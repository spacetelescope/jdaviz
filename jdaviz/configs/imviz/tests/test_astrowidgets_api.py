import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from numpy.testing import assert_allclose


class TestAstrowidgetsAPI:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_app):
        hdu = fits.ImageHDU(np.zeros((10, 10)), name='SCI')

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
        imviz_app.load_data(hdu, data_label='has_wcs')

        # Data without WCS
        imviz_app.load_data(hdu, data_label='no_wcs')
        imviz_app.app.data_collection[1].coords = None

        self.wcs = WCS(hdu.header)
        self.imviz = imviz_app
        self.viewer = imviz_app.app.get_viewer('viewer-1')

    def test_center_offset_pixel(self):
        self.imviz.center_on((0, 1))
        assert_allclose(self.viewer.state.x_min, -5)
        assert_allclose(self.viewer.state.y_min, -4)
        assert_allclose(self.viewer.state.x_max, 5)
        assert_allclose(self.viewer.state.y_max, 6)

        self.imviz.offset_to(1, -1)
        assert_allclose(self.viewer.state.x_min, -4)
        assert_allclose(self.viewer.state.y_min, -5)
        assert_allclose(self.viewer.state.x_max, 6)
        assert_allclose(self.viewer.state.y_max, 5)

    def test_center_offset_sky(self):
        # Blink to the one with WCS because the last loaded data is shown.
        self.viewer.blink_once()

        sky = self.wcs.pixel_to_world(0, 1)
        self.imviz.center_on(sky)
        assert_allclose(self.viewer.state.x_min, -5)
        assert_allclose(self.viewer.state.y_min, -4)
        assert_allclose(self.viewer.state.x_max, 5)
        assert_allclose(self.viewer.state.y_max, 6)

        dsky = 0.1 * u.arcsec
        self.imviz.offset_to(dsky, dsky, skycoord_offset=True)
        assert_allclose(self.viewer.state.x_min, -5.100000000142565)
        assert_allclose(self.viewer.state.y_min, -3.90000000002971)
        assert_allclose(self.viewer.state.x_max, 4.899999999857435)
        assert_allclose(self.viewer.state.y_max, 6.09999999997029)

        # astropy requires Quantity
        with pytest.raises(u.UnitTypeError):
            self.imviz.offset_to(0.1, 0.1, skycoord_offset=True)

        # Cannot pass Quantity without specifying skycoord_offset=True
        with pytest.raises(u.UnitConversionError):
            self.imviz.offset_to(dsky, dsky)

        # Blink to the one without WCS
        self.viewer.blink_once()

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.center_on(sky)

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.offset_to(dsky, dsky, skycoord_offset=True)
