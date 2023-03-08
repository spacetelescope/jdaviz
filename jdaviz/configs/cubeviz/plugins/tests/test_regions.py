"""This module tests region handling specific to Cubeviz.
Generic handling logic already covered in
jdaviz/configs/imviz/tests/test_regions.py
"""
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from glue.core.roi import XRangeROI
from regions import PixCoord, CirclePixelRegion, CircleSkyRegion, EllipsePixelRegion
from specutils import Spectrum1D

from jdaviz.configs.imviz.tests.test_regions import BaseRegionHandler


class TestLoadRegions(BaseRegionHandler):
    @pytest.fixture(autouse=True)
    def setup_class(self, cubeviz_helper, image_cube_hdu_obj_microns):
        cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label='has_microns')
        self.cubeviz = cubeviz_helper
        self.viewer = cubeviz_helper.default_viewer  # This is used in BaseRegionHandler
        self.spectrum_viewer = cubeviz_helper.app.get_viewer(
            cubeviz_helper._default_spectrum_viewer_reference_name
        )

    def teardown_method(self, method):
        """Clear all the subsets for the next test method."""
        self.cubeviz._delete_all_regions()

    def test_regions_mask(self):
        mask = np.zeros((9, 10), dtype=np.bool_)
        mask[0, 0] = True
        bad_regions = self.cubeviz.load_regions([mask], return_bad_regions=True)

        # TODO: Update expected results if we ever support masked Subset in Cubeviz.
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

    def test_regions_pixel(self):
        # A little out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        bad_regions = self.cubeviz.load_regions([my_reg], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1', count=1)
        assert len(self.cubeviz.get_interactive_regions()) == 1

    def test_regions_sky_has_wcs(self):
        sky = SkyCoord(205.4397, 27.0035, unit='deg')
        my_reg_sky_1 = CircleSkyRegion(center=sky, radius=0.0004 * u.deg)
        bad_regions = self.cubeviz.load_regions(my_reg_sky_1, return_bad_regions=True)

        # TODO: Update expected results when we support sky regions in Cubeviz.
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

    def test_spatial_spectral_mix(self):
        # Manually draw ellipse.
        self.cubeviz._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 8))

        # Manually draw wavelength range.
        self.spectrum_viewer.apply_roi(XRangeROI(4.892, 4.896))
        self.cubeviz.app.session.edit_subset_mode.edit_subset = None

        # Get interactive spatial regions only.
        spatial_subsets = self.cubeviz.get_interactive_regions()
        assert list(spatial_subsets.keys()) == ['Subset 1'], spatial_subsets
        assert isinstance(spatial_subsets['Subset 1'], EllipsePixelRegion)

        # NOTE: This does not test that spectrum from Subset is actually scientifically accurate.
        # Get spectral regions only.
        # https://github.com/spacetelescope/jdaviz/issues/1584
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
            spectral_subsets = self.cubeviz.specviz.get_spectra()
        assert list(spectral_subsets.keys()) == ['has_microns[FLUX]',
                                                 'has_microns[FLUX] (Subset 1)',
                                                 'has_microns[FLUX] (Subset 2)'], spectral_subsets  # noqa
        for sp in spectral_subsets.values():
            assert isinstance(sp, Spectrum1D)
