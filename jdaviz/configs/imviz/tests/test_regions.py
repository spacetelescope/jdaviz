import warnings

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.utils.data import get_pkg_data_filename
from numpy.testing import assert_allclose
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
        self.imviz.app.delete_subsets()

    def test_regions_invalid(self):
        # Wrong object
        bad_regions = self.subset_plugin.import_region([self.imviz], return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

        # Sky region on image without WCS
        sky = SkyCoord(337.51894337, -20.83208305, unit='deg')
        reg = CircleSkyRegion(center=sky, radius=0.0004 * u.deg)
        bad_regions = self.subset_plugin.import_region([reg], refdata_label='no_wcs[SCI,1]',
                                                       return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        reg = SkyCircularAperture(sky, 0.5 * u.arcsec)
        bad_regions = self.subset_plugin.import_region([reg], refdata_label='no_wcs[SCI,1]',
                                                       return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        reg = CircleAnnulusSkyRegion(center=sky, inner_radius=0.0004 * u.deg,
                                     outer_radius=0.0005 * u.deg)
        bad_regions = self.subset_plugin.import_region([reg], refdata_label='no_wcs[SCI,1]',
                                                       return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

        # Unsupported functionality
        reg = PointSkyRegion(center=sky)
        bad_regions = self.subset_plugin.import_region(reg, return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Failed to load: NotImplementedError()'  # noqa

        # Out-of-bounds masked subset (pix)
        reg = PolygonPixelRegion(vertices=PixCoord(x=[11, 12, 12], y=[11, 11, 12]))
        bad_regions = self.subset_plugin.import_region(reg, return_bad_regions=True)
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

        # Make sure nothing is returned when not requested even on failure
        bad_regions = self.subset_plugin.import_region(reg)
        assert bad_regions is None

        # Make sure nothing is actually loaded
        self.verify_region_loaded('MaskedSubset 1', count=0)
        assert self.imviz.plugins['Subset Tools'].get_regions() == {}

    def test_regions_fully_out_of_bounds(self):
        """Glue ROI will not error when out of bounds."""
        my_reg = CirclePixelRegion(center=PixCoord(x=100, y=100), radius=5)
        bad_regions = self.subset_plugin.import_region([my_reg], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.plugins['Subset Tools'].get_regions()) == 1

    def test_regions_mask(self):
        mask = np.zeros((10, 10), dtype=np.bool_)
        mask[0, 0] = True
        bad_regions = self.subset_plugin.import_region([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 1')
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Regions skipped: MaskedSubset 1')
            assert self.imviz.plugins['Subset Tools'].get_regions() == {}

        mask[1, 1] = True
        bad_regions = self.subset_plugin.import_region([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 2')
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Regions skipped: MaskedSubset 1')
            assert self.imviz.plugins['Subset Tools'].get_regions() == {}

        # Also test deletion by label here.
        self.imviz.app.delete_subsets('MaskedSubset 1')
        self.verify_region_loaded('MaskedSubset 1', count=0)

        # Adding another mask will increment from 2 even when 1 is now available.
        mask[2, 2] = True
        bad_regions = self.subset_plugin.import_region([mask], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('MaskedSubset 3')
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Regions skipped: MaskedSubset 2, MaskedSubset 3')
            assert self.imviz.plugins['Subset Tools'].get_regions() == {}

        # Deletion of non-existent label raises error
        with pytest.raises(ValueError, match=r'foo not in data collection, can not delete\.'):
            self.imviz.app.delete_subsets('foo')

    def test_regions_pixel(self):
        # A little out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        bad_regions = self.subset_plugin.import_region([my_reg], return_bad_regions=True,
                                                       combination_mode='new')
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        st = self.imviz.plugins['Subset Tools']
        assert len(st.get_regions()) == 1
        # test passing in the subset label as well
        assert len(st.get_regions(list_of_subset_labels='Subset 1')) == 1

    def test_regions_sky_has_wcs(self):
        my_reg_pix_1 = CirclePixelRegion(center=PixCoord(x=2.55, y=3.55), radius=1.05)
        my_reg_pix_2 = EllipsePixelRegion(center=PixCoord(x=1.5, y=2.25), width=7.0, height=4.5)
        my_reg_pix_3 = RectanglePixelRegion(center=PixCoord(x=5.0, y=5.0), width=10, height=10)

        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        # These will become indistinguishable from normal Subset.
        my_reg_sky_1 = CircleSkyRegion(sky, Angle(0.5, u.arcsec))
        my_reg_sky_2 = CircleAnnulusSkyRegion(center=sky, inner_radius=0.0004 * u.deg,
                                              outer_radius=0.0005 * u.deg)
        # Masked subset.
        my_reg_poly_1 = PolygonPixelRegion(vertices=PixCoord(x=[1, 1, 3, 3, 1], y=[1, 3, 3, 1, 1]))

        # Add them all.
        bad_regions = self.subset_plugin.import_region(
            [my_reg_pix_1, my_reg_sky_1, my_reg_sky_2, my_reg_poly_1, my_reg_pix_2, my_reg_pix_3],
            return_bad_regions=True, combination_mode='new')
        assert len(bad_regions) == 0

        # Check regions. We do not check if the translation is correct,
        # that check hopefully is already done in glue-astronomy.
        # Polygon becomes MaskedSubset 1, thus cannot round-trip but made Subset 4 name unavailable.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Regions skipped: MaskedSubset 1')
            subsets = self.imviz.plugins['Subset Tools'].get_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3', 'Subset 5', 'Subset 6'], subsets  # noqa: E501
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)
        assert isinstance(subsets['Subset 3'], CircleAnnulusPixelRegion)
        assert isinstance(subsets['Subset 5'], EllipsePixelRegion)
        assert isinstance(subsets['Subset 6'], RectanglePixelRegion)

        # Polygon becomes MaskedSubset 1.
        self.verify_region_loaded('MaskedSubset 1')

    def test_regions_annulus_from_load_data(self):
        # This file actually will load 2 annuli
        regfile = get_pkg_data_filename('data/ds9_annulus_01.reg')
        self.imviz.load_data(regfile)
        assert len(self.imviz.app.data_collection) == 2  # Make sure not loaded as data

        # Test data is set up such that 1 pixel is 1 arcsec.
        subset_radii = {"Subset 1": [0.5, 1], "Subset 2": [1, 3]}

        subsets = self.imviz.plugins['Subset Tools'].get_regions()
        subset_names = sorted(subsets.keys())
        assert subset_names == ['Subset 1', 'Subset 2']
        for n in subset_names:
            assert isinstance(subsets[n], CircleAnnulusPixelRegion)
            assert_allclose(subsets[n].center.xy, 4.5, rtol=5e-6)
            assert_allclose([subsets[n].inner_radius, subsets[n].outer_radius], subset_radii[n])

    def test_photutils_pixel(self):
        my_aper = CircularAperture((5, 5), r=2)
        bad_regions = self.subset_plugin.import_region([my_aper], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.plugins['Subset Tools'].get_regions()) == 1

    def test_photutils_sky_has_wcs(self):
        sky = SkyCoord(ra=337.5202808, dec=-20.833333059999998, unit='deg')
        my_aper_sky = SkyCircularAperture(sky, 0.5 * u.arcsec)
        bad_regions = self.subset_plugin.import_region([my_aper_sky], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1')
        assert len(self.imviz.plugins['Subset Tools'].get_regions()) == 1


class TestLoadRegionsFromFile(BaseRegionHandler):

    def setup_class(self):
        self.region_file = get_pkg_data_filename(
            'data/ds9.fits.reg', package='regions.io.ds9.tests')
        self.arr = np.ones((1024, 1024))
        self.raw_regions = Regions.read(self.region_file, format='ds9')

    def test_ds9_load_all(self, imviz_helper):
        with pytest.raises(ValueError, match="Cannot load regions without data"):
            imviz_helper.load_data(self.region_file)

        self.viewer = imviz_helper.default_viewer._obj
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.plugins['Subset Tools'].import_region(
            self.region_file, combination_mode='new', return_bad_regions=True)
        assert len(bad_regions) == 1

        # Will load 8/9 and 7 of that become ROIs.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Regions skipped: MaskedSubset 1')
            subsets = imviz_helper.plugins['Subset Tools'].get_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3',
                                        'Subset 4', 'Subset 5', 'Subset 6', 'Subset 7'], subsets

        # The other 1 is MaskedSubset
        self.verify_region_loaded('MaskedSubset 1', count=1)

    def test_ds9_load_two_good(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer._obj
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.plugins['Subset Tools'].import_region(
            self.region_file, combination_mode='new', max_num_regions=2, return_bad_regions=True)
        assert len(bad_regions) == 0
        subsets = imviz_helper.plugins['Subset Tools'].get_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2'], subsets
        self.verify_region_loaded('MaskedSubset 1', count=0)

    def test_ds9_load_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer._obj
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.plugins['Subset Tools'].import_region(
            self.raw_regions[6], return_bad_regions=True)
        assert len(bad_regions) == 1
        assert imviz_helper.plugins['Subset Tools'].get_regions() == {}
        self.verify_region_loaded('MaskedSubset 1', count=0)

    def test_ds9_load_one_good_one_bad(self, imviz_helper):
        self.viewer = imviz_helper.default_viewer._obj
        imviz_helper.load_data(self.arr, data_label='my_image')
        bad_regions = imviz_helper.plugins['Subset Tools'].import_region(
            [self.raw_regions[3], self.raw_regions[6]], return_bad_regions=True)
        assert len(bad_regions) == 1

        subsets = imviz_helper.plugins['Subset Tools'].get_regions()
        assert list(subsets.keys()) == ['Subset 1'], subsets
        self.verify_region_loaded('MaskedSubset 1', count=0)


class TestGetRegions(BaseImviz_WCS_NoWCS):
    def test_annulus(self):
        self.imviz.plugins['Subset Tools'].import_region([
            CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5),  # Outer circle
            CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=2.5),  # Inner circle
        ], combination_mode="new")

        # At this point, there should be two normal circles.
        subsets = self.imviz.plugins['Subset Tools'].get_regions()
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)
        assert subsets['Subset 1'].center == PixCoord(4.5, 4.5)
        assert subsets['Subset 2'].center == PixCoord(4.5, 4.5)
        # ensure agreement between app.get_subsets and subset_tools.get_regions
        ss = self.imviz.app.get_subsets()
        assert ss['Subset 1'][0]['region'] == subsets['Subset 1']
        assert ss['Subset 2'][0]['region'] == subsets['Subset 2']

        # Create a third subset that is an annulus.
        self.imviz.plugins['Subset Tools'].combination_mode = "new"
        subset_groups = self.imviz.app.data_collection.subset_groups
        new_subset = subset_groups[0].subset_state & ~subset_groups[1].subset_state
        self.viewer.apply_subset_state(new_subset)

        subsets = self.imviz.plugins['Subset Tools'].get_regions()
        assert len(self.imviz.app.data_collection.subset_groups) == 3
        assert list(subsets.keys()) == ['Subset 1', 'Subset 2', 'Subset 3'], subsets
        assert isinstance(subsets['Subset 1'], CirclePixelRegion)
        assert isinstance(subsets['Subset 2'], CirclePixelRegion)
        assert isinstance(subsets['Subset 3'], CircleAnnulusPixelRegion)
        # and check the new retrieved region
        assert subsets['Subset 3'].center == PixCoord(4.5, 4.5)

        # Clear the regions for next test.
        self.imviz.app.delete_subsets()
        assert len(self.imviz.app.data_collection.subset_groups) == 0
