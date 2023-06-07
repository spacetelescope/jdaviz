import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.utils.data import get_pkg_data_filename
from photutils.aperture import CircularAperture, SkyCircularAperture
from regions import (PixCoord, CircleSkyRegion, RectanglePixelRegion, CirclePixelRegion,
                     EllipsePixelRegion, PointSkyRegion, PolygonPixelRegion,
                     CircleAnnulusPixelRegion, CircleAnnulusSkyRegion, Regions)

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


class TestLoadRegions(BaseImviz_WCS_NoWCS, BaseRegionHandler):
    def teardown_method(self, method):
        """Clear all the subsets for the next test method."""
        self.imviz._delete_all_regions()

    def test_regions_invalid(self):
        # Wrong object
        bad_regions = self.imviz.load_regions([self.imviz], return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

        # Sky region on image without WCS
        sky = SkyCoord(337.51894337, -20.83208305, unit='deg')
        reg = CircleSkyRegion(center=sky, radius=0.0004 * u.deg)
        bad_regions = self.imviz.load_regions([reg], refdata_label='no_wcs[SCI,1]',
                                              return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        reg = SkyCircularAperture(sky, 0.5 * u.arcsec)
        bad_regions = self.imviz.load_regions([reg], refdata_label='no_wcs[SCI,1]',
                                              return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        reg = CircleAnnulusSkyRegion(center=sky, inner_radius=0.0004 * u.deg,
                                     outer_radius=0.0005 * u.deg)
        bad_regions = self.imviz.load_regions([reg], refdata_label='no_wcs[SCI,1]',
                                              return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        # Unsupported functionality from outside load_regions
        reg = PointSkyRegion(center=sky)
        bad_regions = self.imviz.load_regions(reg, return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Failed to load: NotImplementedError()'  # noqa

        # Out-of-bounds masked subset (pix)
        reg = PolygonPixelRegion(vertices=PixCoord(x=[11, 12, 12], y=[11, 11, 12]))
        bad_regions = self.imviz.load_regions(reg, return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

        # Make sure nothing is returned when not requested even on failure
        bad_regions = self.imviz.load_regions(reg)
        assert bad_regions is None

        # Make sure nothing is actually loaded
        self.verify_region_loaded('MaskedSubset 1', count=0)
        assert self.imviz.get_interactive_regions() == {}

    def test_regions_fully_out_of_bounds(self):
        """Glue ROI will not error when out of bounds."""
        my_reg = CirclePixelRegion(center=PixCoord(x=100, y=100), radius=5)
        bad_regions = self.imviz.load_regions([my_reg], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.get_interactive_regions()) == 1

    def test_regions_mask(self):
        mask = np.zeros((10, 10), dtype=np.bool_)
        mask[0, 0] = True
        bad_regions = self.imviz.load_regions([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 1')
        assert self.imviz.get_interactive_regions() == {}

        mask[1, 1] = True
        bad_regions = self.imviz.load_regions([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 2')
        assert self.imviz.get_interactive_regions() == {}

        # Also test deletion by label here.
        self.imviz._delete_region('MaskedSubset 1')
        self.verify_region_loaded('MaskedSubset 1', count=0)

        # Adding another mask will increment from 2 even when 1 is now available.
        mask[2, 2] = True
        bad_regions = self.imviz.load_regions([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 3')
        assert self.imviz.get_interactive_regions() == {}

        # Deletion of non-existent label is silent no-op.
        self.imviz._delete_region('foo')

    def test_regions_pixel(self):
        # A little out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        bad_regions = self.imviz.load_regions([my_reg], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.get_interactive_regions()) == 1

    def test_regions_sky_has_wcs(self):
        # Mimic interactive region (before)
        self.imviz._apply_interactive_region('bqplot:circle', (1.5, 2.5), (3.6, 4.6))

        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        # These will become indistinguishable from normal Subset.
        my_reg_sky_1 = CircleSkyRegion(sky, Angle(0.5, u.arcsec))
        my_reg_sky_2 = CircleAnnulusSkyRegion(center=sky, inner_radius=0.0004 * u.deg,
                                              outer_radius=0.0005 * u.deg)
        # Masked subset.
        my_reg_sky_3 = PolygonPixelRegion(vertices=PixCoord(x=[1, 1, 3, 3, 1], y=[1, 3, 3, 1, 1]))
        # Add them all.
        bad_regions = self.imviz.load_regions([my_reg_sky_1, my_reg_sky_2, my_reg_sky_3],
                                              return_bad_regions=True)
        assert len(bad_regions) == 0

        # Mimic interactive regions (after)
        self.imviz._apply_interactive_region('bqplot:ellipse', (-2, 0), (5, 4.5))
        self.imviz._apply_interactive_region('bqplot:rectangle', (0, 0), (10, 10))

        # Check interactive regions. We do not check if the translation is correct,
        # that check hopefully is already done in glue-astronomy.
        # Apparently, static region ate up one number...
        subsets = self.imviz.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3', 'Subset 5', 'Subset 6'], subsets  # noqa: E501
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)
        assert isinstance(subsets['Subset 3'], CircleAnnulusPixelRegion)
        assert isinstance(subsets['Subset 5'], EllipsePixelRegion)
        assert isinstance(subsets['Subset 6'], RectanglePixelRegion)

        # Check static region
        self.verify_region_loaded('MaskedSubset 1')

    def test_regions_annulus_from_load_data(self):
        # This file actually will load 2 annuli
        regfile = get_pkg_data_filename('data/ds9_annulus_01.reg')
        self.imviz.load_data(regfile)
        assert len(self.imviz.app.data_collection) == 2  # Make sure not loaded as data

        subsets = self.imviz.get_interactive_regions()
        subset_names = list(subsets.keys())
        assert subset_names == ['Subset 1', 'Subset 2']
        for n in subset_names:
            assert isinstance(subsets[n], CircleAnnulusPixelRegion)

    def test_photutils_pixel(self):
        my_aper = CircularAperture((5, 5), r=2)
        bad_regions = self.imviz.load_regions([my_aper], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.get_interactive_regions()) == 1

    def test_photutils_sky_has_wcs(self):
        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_aper_sky = SkyCircularAperture(sky, 0.5 * u.arcsec)
        bad_regions = self.imviz.load_regions([my_aper_sky], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.get_interactive_regions()) == 1


class TestLoadRegionsFromFile(BaseRegionHandler):

    def setup_class(self):
        self.region_file = get_pkg_data_filename(
            'data/ds9.fits.reg', package='regions.io.ds9.tests')
        self.arr = np.ones((1024, 1024))
        self.raw_regions = Regions.read(self.region_file, format='ds9')

    def test_ds9_load_all(self, imviz_helper):
        with pytest.raises(ValueError, match="Cannot load regions without data"):
            imviz_helper.load_data(self.region_file)

        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.load_regions_from_file(self.region_file, return_bad_regions=True)
        assert len(bad_regions) == 1

        # Will load 8/9 and 7 of that become ROIs.
        subsets = imviz_helper.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3',
                                        'Subset 4', 'Subset 5', 'Subset 6', 'Subset 7'], subsets

        # The other 1 is MaskedSubset
        self.verify_region_loaded('MaskedSubset 1', count=1)

    def test_ds9_load_two_good(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.load_regions_from_file(
            self.region_file, max_num_regions=2, return_bad_regions=True)
        assert len(bad_regions) == 0
        subsets = imviz_helper.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2'], subsets
        self.verify_region_loaded('MaskedSubset 1', count=0)

    def test_ds9_load_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.load_regions(self.raw_regions[6], return_bad_regions=True)
        assert len(bad_regions) == 1
        assert imviz_helper.get_interactive_regions() == {}
        self.verify_region_loaded('MaskedSubset 1', count=0)

    def test_ds9_load_one_good_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.load_regions(
            [self.raw_regions[3], self.raw_regions[6]], return_bad_regions=True)
        assert len(bad_regions) == 1

        subsets = imviz_helper.get_interactive_regions()
        assert list(subsets.keys()) == ['Subset 1'], subsets
        self.verify_region_loaded('MaskedSubset 1', count=0)


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

        # Create a third subset that is an annulus.
        subset_groups = self.imviz.app.data_collection.subset_groups
        new_subset = subset_groups[0].subset_state & ~subset_groups[1].subset_state
        self.viewer.apply_subset_state(new_subset)

        subsets = self.imviz.get_interactive_regions()
        assert len(self.imviz.app.data_collection.subset_groups) == 3
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)
        assert isinstance(subsets['Subset 3'], CircleAnnulusPixelRegion)

        # Clear the regions for next test.
        self.imviz._delete_all_regions()
        assert len(self.imviz.app.data_collection.subset_groups) == 0
