import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose
from regions import EllipseSkyRegion, RectangleSkyRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestDefaultOrientation(BaseImviz_WCS_WCS):
    def test_affine_reset_and_linktype(self):
        lc_plugin = self.imviz.plugins['Orientation']

        lc_plugin.link_type = 'WCS'
        lc_plugin.wcs_use_affine = False
        assert self.imviz.get_link_type("Default orientation", "has_wcs_2[SCI,1]") == "wcs"

        # wcs_use_affine should revert/default to True when change back to Pixels.
        lc_plugin.link_type = 'Pixels'
        assert lc_plugin.wcs_use_affine is True
        assert self.imviz.get_link_type("has_wcs_1[SCI,1]", "has_wcs_2[SCI,1]") == "pixels"

        assert self.imviz.get_link_type("has_wcs_1[SCI,1]", "has_wcs_1[SCI,1]") == "self"

        with pytest.raises(ValueError, match=".*combo not found"):
            self.imviz.get_link_type("has_wcs_1[SCI,1]", "foo")

    def test_astrowidgets_markers_disable_relinking(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'Pixels'

        # Adding markers should disable changing linking from both UI and API.
        assert lc_plugin._obj.need_clear_astrowidget_markers is False
        tbl = Table({'x': (0, 0), 'y': (0, 1)})
        self.viewer.add_markers(tbl, marker_name='xy_markers')

        assert lc_plugin._obj.need_clear_astrowidget_markers is True
        with pytest.raises(ValueError, match="cannot change linking"):
            lc_plugin.link_type = 'WCS'
        assert lc_plugin.link_type == 'Pixels'

        lc_plugin._obj.vue_reset_astrowidget_markers()

        assert lc_plugin._obj.need_clear_astrowidget_markers is False
        lc_plugin.link_type = 'WCS'

    def test_markers_plugin_recompute_positions_pixels_to_wcs(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'Pixels'

        # Blink to second image, if we have to.
        if self.viewer.top_visible_data_label != "has_wcs_2[SCI,1]":
            self.viewer.blink_once()

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        mp = self.imviz.plugins['Markers']

        with mp.as_active():
            # (1, 0) on second image but same sky coordinates as (0, 0) on first.
            label_mouseover._viewer_mouse_event(
                self.viewer, {'event': 'mousemove', 'domain': {'x': 1, 'y': 0}})
            mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown', 'key': 'm'})

            # (0, 0) on first image.
            self.viewer.blink_once()
            label_mouseover._viewer_mouse_event(
                self.viewer, {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
            mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown', 'key': 'm'})

            lc_plugin.link_type = 'WCS'

            # Both marks stay the same in sky, so this means X and Y w.r.t. reference
            # same on both entries.
            # FIXME: 0.25 offset introduced by fake WCS layer (remove AssertionError).
            #        https://jira.stsci.edu/browse/JDAT-4256
            with pytest.raises(AssertionError):
                assert_allclose(mp._obj.marks["imviz-0"].x, 0)
            with pytest.raises(AssertionError):
                assert_allclose(mp._obj.marks["imviz-0"].y, 0)

            mp.clear_table()

    def test_markers_plugin_recompute_positions_wcs_to_pixels(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'

        # Blink to second image, if we have to.
        if self.viewer.top_visible_data_label != "has_wcs_2[SCI,1]":
            self.viewer.blink_once()

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        mp = self.imviz.plugins['Markers']

        with mp.as_active():
            # (0, 0) on second image, but linked by WCS.
            label_mouseover._viewer_mouse_event(
                self.viewer, {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
            mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown', 'key': 'm'})

            # (0, 0) on first image.
            self.viewer.blink_once()
            label_mouseover._viewer_mouse_event(
                self.viewer, {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
            mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown', 'key': 'm'})

            lc_plugin.link_type = 'Pixels'

            # Both marks now get separated, so this means X and Y w.r.t. reference
            # are different on both entries.
            # FIXME: 0.25 offset introduced by fake WCS layer (remove AssertionError).
            #        https://jira.stsci.edu/browse/JDAT-4256
            with pytest.raises(AssertionError):
                assert_allclose(mp._obj.marks["imviz-0"].x, [1, 0])
            with pytest.raises(AssertionError):
                assert_allclose(mp._obj.marks["imviz-0"].y, 0)

            mp.clear_table()


class TestNonDefaultOrientation(BaseImviz_WCS_WCS):
    def test_N_up_multi_viewer(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'

        # Should automatically be applied as reference to first viewer.
        lc_plugin._obj.create_north_up_east_left(set_on_create=True)

        # This would set a different reference to second viewer.
        viewer_2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_1[SCI,1]")
        lc_plugin.viewer = "imviz-1"

        lc_plugin._obj.create_north_up_east_right(set_on_create=True)

        assert self.viewer.state.reference_data.label == "North-up, East-left"
        assert viewer_2.state.reference_data.label == "North-up, East-right"

        # Change orientation in imviz-1 from UI and ensure plugin selection is the same
        lc_plugin.viewer.selected = "imviz-0"
        self.imviz.app._change_reference_data("Default orientation", "imviz-1")
        assert lc_plugin.orientation.selected == "North-up, East-left"

        # Both viewers should revert back to same reference when pixel-linked.
        lc_plugin.link_type = 'Pixels'
        assert self.viewer.state.reference_data.label == "has_wcs_1[SCI,1]"
        assert viewer_2.state.reference_data.label == "has_wcs_1[SCI,1]"

        lc_plugin.link_type = 'WCS'
        assert self.viewer.state.reference_data.label == "Default orientation"
        assert viewer_2.state.reference_data.label == "Default orientation"

    def test_custom_orientation(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'
        lc_plugin.viewer = "imviz-0"

        lc_plugin.rotation_angle = 42  # Triggers auto-label
        lc_plugin._obj.add_orientation(rotation_angle=None, east_left=True, label=None,
                                       set_on_create=True, wrt_data=None)
        assert self.viewer.state.reference_data.label == "CCW 42.00 deg (E-left)"


class TestDeleteOrientation(BaseImviz_WCS_WCS):

    def test_delete_orientation_multi_viewer(self):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'

        # Should automatically be applied as reference to first viewer.
        lc_plugin._obj.create_north_up_east_left(set_on_create=True)

        # This would set a different reference to second viewer.
        viewer_2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_1[SCI,1]")
        lc_plugin.viewer = "imviz-1"
        lc_plugin.orientation = "North-up, East-left"

        self.imviz.app.vue_data_item_remove({"item_name": "North-up, East-left"})

        assert self.viewer.state.reference_data.label == "Default orientation"
        assert viewer_2.state.reference_data.label == "Default orientation"

    @pytest.mark.parametrize("klass", [EllipseSkyRegion, RectangleSkyRegion])
    @pytest.mark.parametrize(
        ("angle", "sbst_theta"),
        [(0.5 * u.rad, 2.641593),
         (-0.5 * u.rad, 3.641589)])
    def test_delete_orientation_with_subset(self, klass, angle, sbst_theta):
        lc_plugin = self.imviz.plugins['Orientation']
        lc_plugin.link_type = 'WCS'

        # Should automatically be applied as reference to first viewer.
        lc_plugin._obj.create_north_up_east_left(set_on_create=True)

        # Create rotated shape
        reg = klass(center=SkyCoord(ra=337.51931488, dec=-20.83187472, unit="deg"),
                    width=2.4 * u.arcsec, height=1.2 * u.arcsec, angle=angle)
        self.imviz.load_regions(reg)

        # Switch to N-up E-right
        lc_plugin._obj.create_north_up_east_right(set_on_create=True)

        self.imviz.app.vue_data_item_remove({"item_name": "North-up, East-left"})

        # Check that E-right still linked to default
        assert len(self.imviz.app.data_collection.external_links) == 3
        assert self.imviz.app.data_collection.external_links[2].data1.label == "North-up, East-right"  # noqa: E501
        assert self.imviz.app.data_collection.external_links[2].data2.label == "Default orientation"

        # Check that the subset got reparented and the angle is correct in the display
        subset_group = self.imviz.app.data_collection.subset_groups[0]
        nuer_data = self.imviz.app.data_collection['North-up, East-right']
        assert subset_group.subset_state.xatt in nuer_data.components
        assert_allclose(subset_group.subset_state.roi.theta, sbst_theta, rtol=1e-5)

        out_reg = self.imviz.app.get_subsets(include_sky_region=True)["Subset 1"][0]["sky_region"]
        assert_allclose(out_reg.center.ra.deg, reg.center.ra.deg)
        assert_allclose(out_reg.center.dec.deg, reg.center.dec.deg)
        assert_quantity_allclose(out_reg.width, reg.width)
        assert_quantity_allclose(out_reg.height, reg.height)
        # FIXME: However, sky angle has to stay the same as per regions convention.
        with pytest.raises(AssertionError, match="Not equal to tolerance"):
            assert_quantity_allclose(out_reg.angle, reg.angle)
