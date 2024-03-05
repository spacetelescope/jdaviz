import numpy as np
from astropy.coordinates import Angle
from astropy.nddata import NDData
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose
from regions import PixCoord, CirclePixelRegion, RectanglePixelRegion, EllipsePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, BaseImviz_WCS_GWCS


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

        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None)

        # Add a subset
        reg = CirclePixelRegion(PixCoord(2, 2), 3).to_sky(self.wcs_1)
        self.imviz.load_regions(reg)

        reg = RectanglePixelRegion(PixCoord(1, 1), 2, 2).to_sky(self.wcs_1)
        self.imviz.load_regions(reg)

        assert len(self.imviz.app.data_collection.subset_groups) == 2

        # by default the parent will be the reference data layer, which
        # is the "Default Orientation" WCS-only layer since Imviz is
        # WCS-linked here. Let's reparent to a layer that we can
        # delete to test the machinery:
        for subset in self.imviz.app.data_collection.subset_groups:
            self.imviz.app._reparent_subsets(
                subset.subset_state.xatt.parent.label,
                "has_wcs_1[SCI,1]"
            )

        subset1 = self.imviz.app.data_collection.subset_groups[0]
        subset2 = self.imviz.app.data_collection.subset_groups[1]
        assert subset1.subset_state.xatt.parent.label == "has_wcs_1[SCI,1]"
        assert_allclose(subset1.subset_state.center(), (2, 2))

        assert subset2.subset_state.xatt.parent.label == "has_wcs_1[SCI,1]"
        assert_allclose(subset2.subset_state.roi.xmin, 0, atol=1e-6)
        assert_allclose(subset2.subset_state.roi.ymin, 0, atol=1e-6)
        assert_allclose(subset2.subset_state.roi.xmax, 2)
        assert_allclose(subset2.subset_state.roi.ymax, 2)

        # We have to remove the data from the viewer before deleting the data from the app.
        self.imviz.app.remove_data_from_viewer("imviz-0", "has_wcs_1[SCI,1]")
        self.imviz.app.vue_data_item_remove({"item_name": "has_wcs_1[SCI,1]"})

        # Make sure we re-linked images 2 and 3 (plus WCS-only reference data layer)
        assert len(self.imviz.app.data_collection.external_links) == 2

        # FIXME: 0.25 offset introduced by fake WCS layer, see
        # https://jira.stsci.edu/browse/JDAT-4256

        # Check that the reparenting and coordinate recalculations happened
        assert subset1.subset_state.xatt.parent.label == "Default orientation"
        assert_allclose(subset1.subset_state.center(), (1.75, 1.75))

        assert subset2.subset_state.xatt.parent.label == "Default orientation"
        assert_allclose(subset2.subset_state.roi.xmin, -0.25)
        assert_allclose(subset2.subset_state.roi.ymin, -0.25)
        assert_allclose(subset2.subset_state.roi.xmax, 1.75)
        assert_allclose(subset2.subset_state.roi.ymax, 1.75)


class TestDeleteWCSLayerWithSubset(BaseImviz_WCS_GWCS):
    """Regression test for https://jira.stsci.edu/browse/JDAT-3958"""
    def test_delete_wcs_layer_with_subset(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'

        # Should automatically be applied as reference to first viewer.
        lc_plugin._obj.create_north_up_east_left(set_on_create=True)

        # Create a rotated ellipse.
        reg = EllipsePixelRegion(
            PixCoord(3.5, 4.5), width=2, height=5, angle=Angle(30, 'deg')).to_sky(self.wcs_1)
        self.imviz.load_regions(reg)

        # Switch back to Default Orientation.
        self.imviz.app._change_reference_data("Default orientation")

        # Delete N-up E-left reference data from GUI.
        self.imviz.app.vue_data_item_remove({"item_name": "North-up, East-left"})

        # Make sure rotated ellipse is still the same as before.
        out_reg_d = self.imviz.app.get_subsets(include_sky_region=True)['Subset 1'][0]['sky_region']
        assert_allclose(reg.center.ra.deg, out_reg_d.center.ra.deg)
        assert_allclose(reg.center.dec.deg, out_reg_d.center.dec.deg)
        assert_quantity_allclose(reg.height, out_reg_d.height)
        assert_quantity_allclose(reg.width, out_reg_d.width)
        assert_quantity_allclose(reg.angle, out_reg_d.angle)
