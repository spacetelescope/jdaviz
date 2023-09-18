from regions import PixCoord, CirclePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_GWCS
from jdaviz.configs.imviz.tests.test_linking import _transform_refdata_pixel_coords


class TestImvizSpatialSubsetCentroid(BaseImviz_WCS_GWCS):
    def test_centroiding(self):
        # FITS WCS and GWCS are rotated from each other.
        self.imviz.link_data(link_type='wcs')

        reg = CirclePixelRegion(PixCoord(2, 2), 3)

        self.imviz.load_regions(reg)

        plg = self.imviz.plugins['Subset Tools']
        plg._obj.subset_selected = 'Subset 1'

        # Since they are linked by pixels, the bright corner pixel aligns
        # and nothing should change.
        coords = _transform_refdata_pixel_coords(
            self.imviz.app.data_collection[-2], self.imviz.app.data_collection[-1],
            in_x=reg.center.x, in_y=reg.center.y
        )

        for i, data_label in enumerate(('fits_wcs[DATA]', 'gwcs[DATA]')):
            plg._obj.dataset_selected = data_label
            plg._obj.set_center(coords, update=True)  # Move the Subset back first.
            plg._obj.vue_recenter_subset()

            # Calculate and move to centroid.
            for j, key in enumerate(("X Center", "Y Center")):
                assert plg._obj._get_value_from_subset_definition(0, key, "value") == coords[j]
                assert plg._obj._get_value_from_subset_definition(0, key, "orig") == coords[j]

            # Radius will not be touched.
            for key in ("value", "orig"):
                assert plg._obj._get_value_from_subset_definition(0, "Radius", key) == 3

        assert plg._obj.get_center() == coords

        # GWCS does not extrapolate and this Subset is out of bounds,
        # so will get NaNs and enter the exception handling logic.
        plg._obj.dataset_selected = 'gwcs[DATA]'
        plg._obj.set_center((2, 2), update=True)  # Move the Subset back first.
        plg._obj.vue_recenter_subset()
        for key in ("X Center", "Y Center"):
            assert plg._obj._get_value_from_subset_definition(0, key, "value") == 2
            assert plg._obj._get_value_from_subset_definition(0, key, "orig") == 2
