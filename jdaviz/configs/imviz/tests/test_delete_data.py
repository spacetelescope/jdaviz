import numpy as np
from astropy.nddata import NDData
from numpy.testing import assert_allclose
from regions import PixCoord, CirclePixelRegion, RectanglePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestDeleteData(BaseImviz_WCS_WCS):

    def test_reparent_str(self):
        for subset in self.imviz.app.data_collection.subset_groups:
            self.imviz.app._reparent_subsets(
                subset.subset_state.xatt.parent.label,
                "has_wcs_1[SCI,1]"
            )

    def test_delete_with_subset_wcs(self):
        # Add a third dataset to test relinking
        arr = np.ones((10, 10))

        # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
        hdu3 = NDData(arr, wcs=self.wcs_1)
        self.imviz.load_data(hdu3, data_label='has_wcs_3')

        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)

        # Add a subset
        reg = CirclePixelRegion(PixCoord(2, 2), 3)
        self.imviz.load_regions(reg)

        reg = RectanglePixelRegion(PixCoord(1, 1), 2, 2)
        self.imviz.load_regions(reg)

        assert len(self.imviz.app.data_collection.subset_groups) == 2

        subset1 = self.imviz.app.data_collection.subset_groups[0]
        subset2 = self.imviz.app.data_collection.subset_groups[1]
        assert subset1.subset_state.xatt.parent.label == "has_wcs_1[SCI,1]"
        assert_allclose(subset1.subset_state.center(), (2, 2))

        assert subset2.subset_state.xatt.parent.label == "has_wcs_1[SCI,1]"
        assert_allclose(subset2.subset_state.roi.xmin, 0)
        assert_allclose(subset2.subset_state.roi.ymin, 0)
        assert_allclose(subset2.subset_state.roi.xmax, 2)
        assert_allclose(subset2.subset_state.roi.ymax, 2)

        # We have to remove the data from the viewer before deleting the data from the app.
        self.imviz.app.remove_data_from_viewer("imviz-0", "has_wcs_1[SCI,1]")
        self.imviz.app.vue_data_item_remove({"item_name": "has_wcs_1[SCI,1]"})

        # Make sure we re-linked images 2 and 3
        assert len(self.imviz.app.data_collection.external_links) == 1

        # Check that the reparenting and coordinate recalculations happened
        assert subset1.subset_state.xatt.parent.label == "has_wcs_2[SCI,1]"
        assert_allclose(subset1.subset_state.center(), (3, 2))

        assert subset2.subset_state.xatt.parent.label == "has_wcs_2[SCI,1]"
        assert_allclose(subset2.subset_state.roi.xmin, 1, atol=1e-6)
        assert_allclose(subset2.subset_state.roi.ymin, 0, atol=1e-6)
        assert_allclose(subset2.subset_state.roi.xmax, 3, atol=1e-6)
        assert_allclose(subset2.subset_state.roi.ymax, 2, atol=1e-6)
