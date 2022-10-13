import numpy as np
from regions import RectanglePixelRegion

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestPanZoomTools(BaseImviz_WCS_WCS):
    def test_panzoom_tools(self):
        v = self.imviz.default_viewer
        v2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer('imviz-1', 'has_wcs_1[SCI,1]')

        t = v.toolbar.tools['jdaviz:boxzoommatch']
        # original limits (x_min, x_max, y_min, y_max): -0.5 9.5 -0.5 9.5
        t.activate()
        t.save_prev_zoom()
        v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max = (1, 8, 1, 8)
        # second viewer should match these changes
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)

        v.toolbar.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa

        v.toolbar.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (1, 8, 1, 8)
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)

        v.toolbar.tools['jdaviz:boxzoommatch'].deactivate()
        v.toolbar.tools['jdaviz:homezoom'].activate()
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)
        v.toolbar.tools['jdaviz:prevzoom'].activate()
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (1, 8, 1, 8)
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)
        t.deactivate()

        t_linkedpan = v.toolbar.tools['jdaviz:panzoommatch']
        t_linkedpan.activate()
        v.center_on((0, 0))
        # make sure both viewers moved to the new center
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-3.5, 3.5, -3.5, 3.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (-3.5, 3.5, -3.5, 3.5)  # noqa
        t_linkedpan.deactivate()

        t_normpan = v.toolbar.tools['jdaviz:imagepanzoom']
        t_normpan.activate()
        t_normpan.on_click({'event': 'click', 'domain': {'x': 1, 'y': 1}})
        # make sure only first viewer re-centered since this mode is not linked mode
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-2.5, 4.5, -2.5, 4.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (-3.5, 3.5, -3.5, 3.5)  # noqa
        t_normpan.deactivate()

        t_linkedpan.activate()
        t_linkedpan.on_click({'event': 'click', 'domain': {'x': 2, 'y': 2}})
        # make sure both viewers moved to the new center
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-1.5, 5.5, -1.5, 5.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (-1.5, 5.5, -1.5, 5.5)  # noqa
        t_linkedpan.deactivate()


# We use a new test class to avoid a dirty state from previous test.
class TestSinglePixelRegion(BaseImviz_WCS_WCS):
    def test_singlepixelregion(self):
        self.imviz.link_data(link_type='wcs')

        t = self.imviz.default_viewer.toolbar.tools['jdaviz:singlepixelregion']
        t.activate()

        # Create a region while viewing reference data.
        t.on_mouse_event({'event': 'click', 'altKey': False, 'domain': {'x': 1, 'y': 2}})
        regions = self.imviz.get_interactive_regions()
        assert len(regions) == 1
        reg = regions['Subset 1']
        assert (isinstance(reg, RectanglePixelRegion) and reg.center.x == 1 and reg.center.y == 2
                and reg.width == 1 and reg.height == 1)

        # Clicking again will move the region, not creating a new one.
        t.on_mouse_event({'event': 'click', 'altKey': False, 'domain': {'x': 2, 'y': 3}})
        regions = self.imviz.get_interactive_regions()
        assert len(regions) == 1
        reg = regions['Subset 1']
        assert (isinstance(reg, RectanglePixelRegion) and reg.center.x == 2 and reg.center.y == 3
                and reg.width == 1 and reg.height == 1)

        # Create a new region while viewing dithered data.
        # Region will still be w.r.t. reference data, that is, x and y from domain stay the same.
        self.imviz.default_viewer.blink_once()
        t.on_mouse_event({'event': 'click', 'altKey': True, 'domain': {'x': 3, 'y': 4}})
        regions = self.imviz.get_interactive_regions()
        assert len(regions) == 2
        reg = regions['Subset 2']
        assert (isinstance(reg, RectanglePixelRegion) and reg.center.x == 3 and reg.center.y == 4
                and reg.width == 1 and reg.height == 1)

        t.deactivate()


def test_blink(imviz_helper):
    viewer = imviz_helper.default_viewer

    for i in range(3):
        imviz_helper.load_data(np.zeros((2, 2)) + i, data_label=f'image_{i}')

    viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b', 'domain': {'x': 0, 'y': 0}})
    assert viewer.label_mouseover.value == '+0.00000e+00 '

    # Blink forward and update coordinates info panel.
    viewer.blink_once()
    viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert viewer.label_mouseover.value == '+1.00000e+00 '

    # Blink backward.
    viewer.blink_once(reversed=True)
    viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert viewer.label_mouseover.value == '+0.00000e+00 '

    # Blink backward again.
    viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'B', 'domain': {'x': 0, 'y': 0}})
    assert viewer.label_mouseover.value == '+2.00000e+00 '


def test_compass_open_while_load(imviz_helper):
    plg = imviz_helper.plugins['Compass']
    plg.open_in_tray()

    # Should not crash even if Compass is open in tray.
    imviz_helper.load_data(np.ones((2, 2)))
    assert len(imviz_helper.app.data_collection) == 1
