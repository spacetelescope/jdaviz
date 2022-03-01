import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.utils.data import get_pkg_data_filename
from photutils import CircularAperture, SkyCircularAperture
from regions import (PixCoord, CircleSkyRegion, RectanglePixelRegion, CirclePixelRegion,
                     EllipsePixelRegion, PointPixelRegion, PointSkyRegion, Regions)

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class BaseRegionHandler:
    """Test to see if region is loaded.
    Does not check if region is actually at the correct place in display.
    """
    def verify_region_loaded(self, region_label, count=2):
        n = 0
        for layer in self.viewer.state.layers:
            if layer.layer.label == region_label:
                n += 1
                assert layer.visible
        assert n == count


class TestLoadStaticRegions(BaseImviz_WCS_NoWCS, BaseRegionHandler):

    @pytest.mark.parametrize(('subset_label', 'warn_msg'),
                             [('reg', 'Unsupported region type'),
                              ('Subset 1', 'is not allowed, skipping')])
    def test_regions_invalid(self, subset_label, warn_msg):
        # Does not matter if region is invalid here, it is skipped.
        with pytest.warns(UserWarning, match=warn_msg):
            bad_regions = self.imviz.load_static_regions({subset_label: self.imviz})
        assert len(bad_regions) == 1
        self.verify_region_loaded(subset_label, count=0)
        assert self.imviz.get_interactive_regions() == {}  # Subset case should not confused it

    def test_regions_fully_out_of_bounds(self):
        my_reg = CirclePixelRegion(center=PixCoord(x=100, y=100), radius=5)
        with pytest.warns(UserWarning, match='failed to load, skipping'):
            bad_regions = self.imviz.load_static_regions({'my_oob_reg': my_reg})
        assert len(bad_regions) == 1

        # BUG: https://github.com/glue-viz/glue/issues/2275
        self.verify_region_loaded('my_oob_reg', count=1)  # Should be: count=0

    def test_regions_mask(self):
        mask = np.zeros((10, 10), dtype=np.bool_)
        mask[0, 0] = True
        bad_regions = self.imviz.load_static_regions({'my_mask': mask})
        assert len(bad_regions) == 0
        self.verify_region_loaded('my_mask')
        assert self.imviz.get_interactive_regions() == {}

        # Also test deletion by label here.
        self.imviz._delete_region('my_mask')
        self.verify_region_loaded('my_mask', count=0)

        # Deletion of non-existent label is silent no-op.
        self.imviz._delete_region('foo')

    def test_regions_pixel(self):
        # A little out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        bad_regions = self.imviz.load_static_regions({'my_reg': my_reg})
        assert len(bad_regions) == 0
        self.verify_region_loaded('my_reg')

        # Unsupported shape but a valid region
        my_pt_reg = PointPixelRegion(center=PixCoord(x=1, y=1))
        with pytest.warns(UserWarning, match='failed to load, skipping'):
            bad_regions = self.imviz.load_static_regions({'my_pt_reg': my_pt_reg})
        assert len(bad_regions) == 1
        self.verify_region_loaded('my_pt_reg', count=0)

        assert self.imviz.get_interactive_regions() == {}

    # We attach a basic get_interactive_regions test here too.
    def test_regions_sky_has_wcs(self):
        # Mimic interactive region (before)
        self.imviz._apply_interactive_region('bqplot:circle', (1.5, 2.5), (3.6, 4.6))

        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_reg_sky = CircleSkyRegion(sky, Angle(0.5, u.arcsec))
        bad_regions = self.imviz.load_static_regions({'my_reg_sky_1': my_reg_sky})
        assert len(bad_regions) == 0

        # Unsupported shape but a valid region
        my_pt_reg_sky = PointSkyRegion(center=sky)
        with pytest.warns(UserWarning, match='failed to load, skipping'):
            bad_regions = self.imviz.load_static_regions({'my_pt_reg_sky_1': my_pt_reg_sky})
        assert len(bad_regions) == 1

        # Mimic interactive regions (after)
        self.imviz._apply_interactive_region('bqplot:ellipse', (-2, 0), (5, 4.5))
        self.imviz._apply_interactive_region('bqplot:rectangle', (0, 0), (10, 10))

        # Check interactive regions. We do not check if the translation is correct,
        # that check hopefully is already done in glue-astronomy.
        # Apparently, static region ate up one number...
        subsets = self.imviz.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 3', 'Subset 4'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 3'], EllipsePixelRegion)
        assert isinstance(subsets['Subset 4'], RectanglePixelRegion)

        # Check static region
        self.verify_region_loaded('my_reg_sky_1')
        self.verify_region_loaded('my_pt_reg_sky_1', count=0)

    def test_photutils_pixel(self):
        my_aper = CircularAperture((5, 5), r=2)
        bad_regions = self.imviz.load_static_regions({'my_aper': my_aper})
        assert len(bad_regions) == 0
        self.verify_region_loaded('my_aper')
        assert self.imviz.get_interactive_regions() == {}

    def test_photutils_sky_has_wcs(self):
        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_aper_sky = SkyCircularAperture(sky, 0.5 * u.arcsec)
        bad_regions = self.imviz.load_static_regions({'my_aper_sky_1': my_aper_sky})
        assert len(bad_regions) == 0
        self.verify_region_loaded('my_aper_sky_1')
        assert self.imviz.get_interactive_regions() == {}


class TestLoadStaticRegionsFromFile(BaseRegionHandler):

    def setup_class(self):
        self.region_file = get_pkg_data_filename(
            'data/ds9.fits.reg', package='regions.io.ds9.tests')
        self.arr = np.ones((1024, 1024))
        self.raw_regions = Regions.read(self.region_file, format='ds9')

    def test_ds9_load_all(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        with pytest.warns(UserWarning):
            bad_regions = imviz_helper.load_static_regions_from_file(self.region_file)
        assert len(bad_regions) == 1
        for i in (0, 1, 2, 3, 4, 5, 7, 8):  # Only these will successfully load
            self.verify_region_loaded(f'region_{i}', count=1)

    def test_ds9_load_two_good(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.load_static_regions_from_file(
            self.region_file, prefix='good', max_num_regions=2)
        assert len(bad_regions) == 0
        for i in range(2):
            self.verify_region_loaded(f'good_{i}', count=1)

    def test_ds9_load_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        with pytest.warns(UserWarning, match='failed to load, skipping'):
            bad_regions = imviz_helper.load_static_regions({'bad_0': self.raw_regions[6]})
        assert len(bad_regions) == 1
        self.verify_region_loaded('bad_0', count=0)

    def test_ds9_load_one_good_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        with pytest.warns(UserWarning, match='failed to load, skipping'):
            bad_regions = imviz_helper.load_static_regions({
                'good_0': self.raw_regions[3],
                'bad_0': self.raw_regions[6]})
        assert len(bad_regions) == 1
        self.verify_region_loaded('good_0', count=1)
        self.verify_region_loaded('bad_0', count=0)


class TestLoadStaticRegionsSkyNoWCS(BaseRegionHandler):
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        # Data without WCS
        imviz_helper.load_data(np.zeros((10, 10)), data_label='no_wcs')

        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer
        self.sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')

    def test_regions_sky_no_wcs(self):
        my_reg_sky = CircleSkyRegion(self.sky, Angle(0.5, u.arcsec))
        with pytest.warns(UserWarning, match='data has no valid WCS'):
            bad_regions = self.imviz.load_static_regions({'my_reg_sky_2': my_reg_sky})
        assert len(bad_regions) == 1
        self.verify_region_loaded('my_reg_sky_2', count=0)
        assert self.imviz.get_interactive_regions() == {}

    def test_photutils_sky_no_wcs(self):
        my_aper_sky = SkyCircularAperture(self.sky, 0.5 * u.arcsec)
        with pytest.warns(UserWarning, match='data has no valid WCS'):
            bad_regions = self.imviz.load_static_regions({'my_aper_sky_2': my_aper_sky})
        assert len(bad_regions) == 1
        self.verify_region_loaded('my_aper_sky_2', count=0)
        assert self.imviz.get_interactive_regions() == {}


class TestGetInteractiveRegions(BaseImviz_WCS_NoWCS):
    def test_annulus(self):
        # Outer circle
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))
        # Inner circle
        self.imviz._apply_interactive_region('bqplot:circle', (2, 2), (7, 7))

        # At this point, there should be two normal circles.
        subsets = self.imviz.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)

        # Turn the inner circle (Subset 2) into annulus.
        subset_groups = self.imviz.app.data_collection.subset_groups
        new_subset = subset_groups[0].subset_state & ~subset_groups[1].subset_state
        self.viewer.apply_subset_state(new_subset)

        # Annulus is no longer accessible by API but also should not crash Imviz.
        subsets = self.imviz.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)

        # Clear the regions for next test.
        self.imviz._delete_all_regions()
