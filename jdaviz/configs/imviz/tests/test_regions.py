import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord, Angle

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS

try:
    import regions  # noqa
    HAS_REGIONS = True
except ImportError:
    HAS_REGIONS = False

try:
    import photutils  # noqa
    HAS_PHOTUTILS = True
except ImportError:
    HAS_PHOTUTILS = False


class BaseRegionHandler:
    """Test to see if region is loaded.
    Does not check if region is actually at the correct place in display.
    """
    def teardown_method(self, method):
        # Make sure each test method did not affect interactive region getter
        # until we implement roundtripping.
        assert self.imviz.get_interactive_regions() == {}

    def verify_region_loaded(self, region_label, count=2):
        n = 0
        for layer in self.viewer.state.layers:
            if layer.layer.label == region_label:
                n += 1
                assert layer.visible
        assert n == count


class TestLoadStaticRegions(BaseImviz_WCS_NoWCS, BaseRegionHandler):

    def test_regions_invalid(self):
        # Does not matter if region is invalid here, it is skipped.
        with pytest.warns(UserWarning, match='Unsupported region type'):
            self.imviz.load_static_regions({'reg': self.imviz})
        with pytest.warns(UserWarning, match='is not allowed, skipping'):
            self.imviz.load_static_regions({'Subset 1': self.imviz})

        self.verify_region_loaded('reg', count=0)
        self.verify_region_loaded('Subset 1', count=0)

    def test_regions_mask(self):
        mask = np.zeros((10, 10), dtype=np.bool_)
        mask[0, 0] = True
        self.imviz.load_static_regions({'my_mask': mask})
        self.verify_region_loaded('my_mask')

    @pytest.mark.skipif(not HAS_REGIONS, reason='regions is missing')
    def test_regions_pixel(self):
        from regions import PixCoord, CirclePixelRegion

        # Out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        self.imviz.load_static_regions({'my_reg': my_reg})
        self.verify_region_loaded('my_reg')

    @pytest.mark.skipif(not HAS_REGIONS, reason='regions is missing')
    def test_regions_sky_has_wcs(self):
        from regions import CircleSkyRegion

        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_reg_sky = CircleSkyRegion(sky, Angle(0.5, u.arcsec))
        self.imviz.load_static_regions({'my_reg_sky_1': my_reg_sky})
        self.verify_region_loaded('my_reg_sky_1')

    @pytest.mark.skipif(not HAS_PHOTUTILS, reason='photutils is missing')
    def test_photutils_pixel(self):
        from photutils import CircularAperture

        my_aper = CircularAperture((5, 5), r=2)
        self.imviz.load_static_regions({'my_aper': my_aper})
        self.verify_region_loaded('my_aper')

    @pytest.mark.skipif(not HAS_PHOTUTILS, reason='photutils is missing')
    def test_photutils_sky_has_wcs(self):
        from photutils import SkyCircularAperture

        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_aper_sky = SkyCircularAperture(sky, 0.5 * u.arcsec)
        self.imviz.load_static_regions({'my_aper_sky_1': my_aper_sky})
        self.verify_region_loaded('my_aper_sky_1')


class TestLoadStaticRegionsSkyNoWCS(BaseRegionHandler):
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_app):
        # Data without WCS
        imviz_app.load_data(np.zeros((10, 10)), data_label='no_wcs')

        self.imviz = imviz_app
        self.viewer = imviz_app.app.get_viewer('viewer-1')
        self.sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')

    @pytest.mark.skipif(not HAS_REGIONS, reason='regions is missing')
    def test_regions_sky_no_wcs(self):
        from regions import CircleSkyRegion

        my_reg_sky = CircleSkyRegion(self.sky, Angle(0.5, u.arcsec))
        with pytest.warns(UserWarning, match='data has no valid WCS'):
            self.imviz.load_static_regions({'my_reg_sky_2': my_reg_sky})
        self.verify_region_loaded('my_reg_sky_2', count=0)

    @pytest.mark.skipif(not HAS_PHOTUTILS, reason='photutils is missing')
    def test_photutils_sky_no_wcs(self):
        from photutils import SkyCircularAperture

        my_aper_sky = SkyCircularAperture(self.sky, 0.5 * u.arcsec)
        with pytest.warns(UserWarning, match='data has no valid WCS'):
            self.imviz.load_static_regions({'my_aper_sky_2': my_aper_sky})
        self.verify_region_loaded('my_aper_sky_2', count=0)
