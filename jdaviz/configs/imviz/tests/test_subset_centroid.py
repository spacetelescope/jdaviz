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
            for key in ("X Center", "Y Center"):
                assert plg._obj._get_value_from_subset_definition(0, key, "value") == -1
                assert plg._obj._get_value_from_subset_definition(0, key, "orig") == -1

            # Radius will not be touched.
            for key in ("value", "orig"):
                assert plg._obj._get_value_from_subset_definition(0, "Radius", key) == 3

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
        data = self.imviz.app.data_collection[plg._obj.dataset_selected]
        # Pixel value is now w.r.t. fake WCS layer, not the selected data.
        for key in ("value", "orig"):
            x = plg._obj._get_value_from_subset_definition(0, "X Center", key)
            y = plg._obj._get_value_from_subset_definition(0, "Y Center", key)
            data_xy = self.viewer._get_real_xy(data, x, y)[:2]
            assert_allclose(data_xy, -1)

        # GWCS does not extrapolate and this Subset is out of bounds,
        # so will get NaNs and enter the exception handling logic.
        plg._obj.dataset_selected = 'gwcs[DATA]'
        plg._obj.set_center((2.6836, 1.6332), update=True)  # Move the Subset back first.
        plg._obj.vue_recenter_subset()
        for key in ("value", "orig"):
            x = plg._obj._get_value_from_subset_definition(0, "X Center", key)
            y = plg._obj._get_value_from_subset_definition(0, "Y Center", key)
            assert_allclose((x, y), (2.6836, 1.6332))

        # The functionality for set_center has changed so that the subset state itself
        # is updated but that change is not propagated to subset_definitions or the UI until
        # vue_update_subset is called.
        plg._obj.set_center((2, 2), update=False)
        for key in ("value", "orig"):
            x = plg._obj._get_value_from_subset_definition(0, "X Center", key)
            y = plg._obj._get_value_from_subset_definition(0, "Y Center", key)
            assert_allclose((x, y), (2.6836, 1.6332))
