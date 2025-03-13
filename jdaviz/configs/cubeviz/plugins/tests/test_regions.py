"""This module tests region handling specific to Cubeviz.
Generic handling logic already covered in
jdaviz/configs/imviz/tests/test_regions.py
"""
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from regions import PixCoord, CirclePixelRegion, CircleSkyRegion, EllipsePixelRegion
from specutils import Spectrum1D, SpectralRegion

from jdaviz.configs.imviz.tests.test_regions import BaseRegionHandler


class TestLoadRegions(BaseRegionHandler):
    @pytest.fixture(autouse=True)
    def setup_class(self, cubeviz_helper, image_cube_hdu_obj_microns):
        self.cubeviz = cubeviz_helper
        cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label='has_microns')
        self.viewer = cubeviz_helper.default_viewer._obj  # This is used in BaseRegionHandler
        self.spectrum_viewer = cubeviz_helper.app.get_viewer(
            cubeviz_helper._default_spectrum_viewer_reference_name
        )

    def teardown_method(self, method):
        """Clear all the subsets for the next test method."""
        self.cubeviz.app.delete_subsets()

    def test_regions_mask(self):
        mask = np.zeros((9, 10), dtype=np.bool_)
        mask[0, 0] = True
        bad_regions = self.cubeviz.plugins['Subset Tools'].import_region(
            [mask], return_bad_regions=True)

        # TODO: Update expected results if we ever support masked Subset in Cubeviz.
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Mask creation failed'

    def test_regions_pixel(self):
        # A little out-of-bounds should still overlay the overlapped part.
        my_reg = CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)
        bad_regions = self.cubeviz.plugins['Subset Tools'].import_region(
            [my_reg], return_bad_regions=True)
        assert len(bad_regions) == 0
        self.verify_region_loaded('Subset 1', count=1)
        assert len(self.cubeviz.plugins['Subset Tools'].get_regions()) == 1

    def test_regions_sky_has_wcs(self):
        sky = SkyCoord(205.4397, 27.0035, unit='deg')
        my_reg_sky_1 = CircleSkyRegion(center=sky, radius=0.0004 * u.deg)
        bad_regions = self.cubeviz.plugins['Subset Tools'].import_region(
            my_reg_sky_1, return_bad_regions=True)

        # TODO: Update expected results when we support sky regions in Cubeviz.
        assert len(bad_regions) == 1 and bad_regions[0][1] == 'Sky region provided but data has no valid WCS'  # noqa

    def test_spatial_spectral_mix(self):
        # Draw ellipse and wavelength range.
        unit = u.Unit(self.cubeviz.plugins['Unit Conversion'].spectral_unit.selected)
        self.cubeviz.plugins['Subset Tools'].import_region([
            EllipsePixelRegion(center=PixCoord(x=4.5, y=4.0), width=9.0, height=8.0),
            SpectralRegion(4.892 * unit, 4.896 * unit)
        ], combination_mode="new")
        self.cubeviz.app.session.edit_subset_mode.edit_subset = None

        # Get spatial regions only.
        st = self.cubeviz.plugins['Subset Tools']._obj
        spatial_subsets_as_regions = st.get_regions(region_type='spatial')
        assert list(spatial_subsets_as_regions.keys()) == ['Subset 1'], spatial_subsets_as_regions
        assert isinstance(spatial_subsets_as_regions['Subset 1'], EllipsePixelRegion)
        # ensure agreement between app.get_subsets and subset_tools.get_regions
        ss = self.cubeviz.app.get_subsets()
        assert ss['Subset 1'][0]['region'] == spatial_subsets_as_regions['Subset 1']

        # NOTE: This does not test that spectrum from Subset is actually scientifically accurate.
        # Get spectral regions only.
        # https://github.com/spacetelescope/jdaviz/issues/1584
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
            spectral_subsets = self.cubeviz.specviz.get_spectra()
        assert list(spectral_subsets.keys()) == ['Spectrum (sum)',
                                                 'Spectrum (sum) (Subset 2)',
                                                 'Spectrum (Subset 1, sum)',
                                                 'Spectrum (Subset 1, sum) (Subset 2)']
        for sp in spectral_subsets.values():
            assert isinstance(sp, Spectrum1D)
