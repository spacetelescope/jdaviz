from astropy import units as u
from astropy.coordinates import SkyCoord
from numpy.testing import assert_allclose
from regions import PixCoord, CirclePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_GWCS


class TestImvizSpatialSubsetCentroidPixelLinked(BaseImviz_WCS_GWCS):
    def test_centroiding_pixel(self):
        reg = CirclePixelRegion(PixCoord(2, 2), 3)
        self.imviz.load_regions(reg)

        plg = self.imviz.plugins['Subset Tools']
        plg._obj.subset_selected = 'Subset 1'

        # Since they are linked by pixels, the bright corner pixel aligns
        # and nothing should change.
        for data_label in ('fits_wcs[DATA]', 'gwcs[DATA]'):
            plg._obj.dataset_selected = data_label
            plg._obj.set_center((2, 2), update=True)  # Move the Subset back first.
            plg._obj.vue_recenter_subset()

            # Calculate and move to centroid.
            for key in ("X Center (pixels)", "Y Center (pixels)"):
                assert plg._obj._get_value_from_subset_definition(0, key, "value") == -1
                assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1

            # Radius will not be touched.
            for key in ("value", "orig"):
                assert plg._obj._get_value_from_subset_definition(0, "Radius (pixels)", key) == 3

        assert plg._obj.get_center() == (-1, -1)


class TestImvizSpatialSubsetCentroidWCSLinked(BaseImviz_WCS_GWCS):
    def test_centroiding_wcs(self):
        # FITS WCS and GWCS are rotated from each other.
        # Plain array always by pixel wrt FITS WCS.
        self.imviz.link_data(link_type='wcs')

        reg = CirclePixelRegion(PixCoord(2, 2), 3).to_sky(self.wcs_1)
        self.imviz.load_regions(reg)

        plg = self.imviz.plugins['Subset Tools']
        plg._obj.subset_selected = 'Subset 1'
        plg._obj.dataset_selected = 'fits_wcs[DATA]'
        plg._obj.vue_recenter_subset()

        # Pixel value is now w.r.t. fake WCS layer, not the selected data.
        for key in ("value", "orig"):
            # subset definition is now in sky coordinates. get RA and Dec and convert back to pixel
            # to compare with expected recentered position.
            ra = plg._obj._get_value_from_subset_definition(0, "RA Center (degrees)", key) * u.deg
            dec = plg._obj._get_value_from_subset_definition(0, "Dec Center (degrees)", key) * u.deg
            x, y = SkyCoord(ra, dec).to_pixel(self.wcs_1)
            assert_allclose((x, y), -1)

        # GWCS does not extrapolate and this Subset is out of bounds,
        # so will get NaNs and enter the exception handling logic.
        plg._obj.dataset_selected = 'gwcs[DATA]'
        plg._obj.set_center((2.6836, 1.6332), update=True)  # Move the Subset back first.
        plg._obj.vue_recenter_subset()
        subsets = self.imviz.app.get_subsets(include_sky_region=True)
        subsets_sky = subsets['Subset 1'][0]['sky_region']
        subsets_pix = subsets['Subset 1'][0]['region']
        assert_allclose((subsets_pix.center.x, subsets_pix.center.y), (2.6836, 1.6332))
        for key in ("value", "orig"):
            ra = plg._obj._get_value_from_subset_definition(0, "RA Center (degrees)", key)
            dec = plg._obj._get_value_from_subset_definition(0, "Dec Center (degrees)", key)

            # make sure what is in subset_definitions matches what is returned by get_subsets
            assert_allclose((ra, dec), (subsets_sky.center.ra.deg, subsets_sky.center.dec.deg))

        # The functionality for set_center has changed so that the subset state itself
        # is updated but that change is not propagated to subset_definitions or the UI until
        # vue_update_subset is called.
        plg._obj.set_center((2, 2), update=False)
        for key in ("value", "orig"):
            ra = plg._obj._get_value_from_subset_definition(0, "RA Center (degrees)", key)
            dec = plg._obj._get_value_from_subset_definition(0, "Dec Center (degrees)", key)
            # here 'ra' and 'dec' should remain unchanged from when they were defined, since
            # vue_update_subset hasn't run
            assert_allclose((ra, dec), (subsets_sky.center.ra.deg, subsets_sky.center.dec.deg))
