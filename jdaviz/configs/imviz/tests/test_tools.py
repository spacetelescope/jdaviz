import numpy as np

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_zoom_tools(self):
        v = self.imviz.default_viewer
        v2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer('imviz-1', 'has_wcs_1[SCI,1]')

        t = v.toolbar_nested.tools['jdaviz:boxzoommatch']
        # original limits (x_min, x_max, y_min, y_max): -0.5 9.5 -0.5 9.5
        t.activate()
        t.save_prev_zoom()
        v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max = (1, 8, 1, 8)
        # second viewer should match these changes
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)

        v.toolbar_nested.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa

        v.toolbar_nested.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (1, 8, 1, 8)
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)

        v.toolbar_nested.tools['jdaviz:boxzoommatch'].deactivate()
        v.toolbar_nested.tools['jdaviz:homezoom'].activate()
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (-0.5, 9.5, -0.5, 9.5)  # noqa
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)
        v.toolbar_nested.tools['jdaviz:prevzoom'].activate()
        assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (1, 8, 1, 8)
        assert (v2.state.x_min, v2.state.x_max, v2.state.y_min, v2.state.y_max) == (1, 8, 1, 8)


def test_blink(imviz_helper):
    viewer = imviz_helper.default_viewer

    for i in range(3):
        imviz_helper.load_data(np.zeros((2, 2)) + i, data_label=f'image_{i}')

    # Last loaded is shown first. So, blinking will take you back to the first one.
    # Blink forward. The event will also initialize viewer.label_mouseover .
    viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b', 'domain': {'x': 0, 'y': 0}})
    assert viewer.label_mouseover.value == '+0.00000e+00 '

    # Blink forward again and update coordinates info panel.
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
