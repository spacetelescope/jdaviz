from regions import PixCoord, CirclePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_GWCS


class TestImvizSpatialSubsetCentroid(BaseImviz_WCS_GWCS):
    def test_centroiding(self):
        reg = CirclePixelRegion(PixCoord(2, 2), 3)
        self.imviz.load_regions(reg)

        plg = self.imviz.plugins['Subset Tools']
        plg._obj.subset_selected = 'Subset 1'

        # Since they are linked by pixels, the bright corner pixel aligns
        # and nothing should change.
        for data_label in ('fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs'):
            plg._obj.dataset_selected = data_label
            plg._obj.set_center((2, 2), update=True)  # Move the Subset back first.
            plg._obj.vue_recenter_subset()

            # Calculate and move to centroid.
            for key in ("X Center", "Y Center"):
                assert plg._obj._get_value_from_subset_definition(0, key, "value") == -1
                assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1

            # Radius will not be touched.
            for key in ("value", "orig"):
                assert plg._obj._get_value_from_subset_definition(0, "Radius", key) == 3

        assert plg._obj.get_center() == (-1, -1)

        # FITS WCS and GWCS are rotated from each other.
        # Plain array always by pixel wrt FITS WCS.
        self.imviz.link_data(link_type='wcs')

        plg._obj.dataset_selected = 'fits_wcs[DATA]'
        plg._obj.set_center((2, 2), update=True)  # Move the Subset back first.
        plg._obj.vue_recenter_subset()
        for key in ("X Center", "Y Center"):
            assert plg._obj._get_value_from_subset_definition(0, key, "value") == -1
            assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1

        # GWCS does not extrapolate and this Subset is out of bounds,
        # so will get NaNs and enter the exception handling logic.
        plg._obj.dataset_selected = 'gwcs[DATA]'
        plg._obj.set_center((2, 2), update=True)  # Move the Subset back first.
        plg._obj.vue_recenter_subset()
        for key in ("X Center", "Y Center"):
            assert plg._obj._get_value_from_subset_definition(0, key, "value") == 2
            assert plg._obj._get_value_from_subset_definition(0, key, "orig") == 2

        # No WCS case will be same as FITS WCS.
        plg._obj.dataset_selected = 'no_wcs'
        plg._obj.vue_recenter_subset()
        for key in ("X Center", "Y Center"):
            assert plg._obj._get_value_from_subset_definition(0, key, "value") == -1
            assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1

        # This ends up not getting used in production but just in case we need it
        # back in the future.
        plg._obj.set_center((2, 2), update=False)
        for key in ("X Center", "Y Center"):
            assert plg._obj._get_value_from_subset_definition(0, key, "value") == 2
            assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1
