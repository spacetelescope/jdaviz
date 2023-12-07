import numpy as np
from astropy import units as u
from astropy.nddata import NDData
from numpy.testing import assert_allclose, assert_array_equal

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestLineProfileXY(BaseImviz_WCS_NoWCS):
    def test_plugin_linked_by_pixel(self):
        """Go through plugin logic but does not check plot contents."""
        lp_plugin = self.imviz.plugins['Imviz Line Profiles (XY)']._obj
        lp_plugin.plugin_opened = True

        assert lp_plugin.viewer.labels == ['imviz-0']
        assert lp_plugin.viewer_selected == 'imviz-0'

        # Plot attempt with null X/Y should not crash but also no-op.
        assert 'line' not in lp_plugin.plot_across_x.layers
        lp_plugin.vue_draw_plot()
        assert not lp_plugin.plot_available

        # Mimic "l" key pressed.
        lp_plugin._on_viewer_key_event(self.viewer,
                                       {'event': 'keydown', 'key': 'l',
                                        'domain': {'x': 5.1, 'y': 5}})
        assert_allclose(lp_plugin.selected_x, 5.1)
        assert_allclose(lp_plugin.selected_y, 5)
        assert len(lp_plugin.plot_across_x.layers['line'].layer.data['x']) > 0
        assert len(lp_plugin.plot_across_y.layers['line'].layer.data['x']) > 0
        assert lp_plugin.plot_available

        # Add data with unit
        ndd = NDData(np.ones((10, 10)), unit=u.nJy)
        self.imviz.load_data(ndd, data_label='ndd', show_in_viewer=False)

        viewer_2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer(viewer_2.reference_id, 'has_wcs[SCI,1]')
        self.imviz.app.add_data_to_viewer(viewer_2.reference_id, 'ndd[DATA]')

        # Blink also triggers viewer takeover and line profile redraw,
        # similar to the "l" key but without touching X and Y.
        viewer_2.blink_once()
        assert lp_plugin.viewer.labels == ['imviz-0', 'imviz-1']
        assert lp_plugin.viewer_selected == 'imviz-1'
        assert_allclose(lp_plugin.selected_x, 5.1)
        assert_allclose(lp_plugin.selected_y, 5)
        assert lp_plugin.plot_across_x.layers['line'].visible
        assert len(lp_plugin.plot_across_x.layers['line'].layer.data['x']) > 0
        assert len(lp_plugin.plot_across_y.layers['line'].layer.data['x']) > 0
        assert lp_plugin.plot_available

        # Wrong input resets plots without error.
        lp_plugin.selected_x = -1
        lp_plugin.vue_draw_plot()
        assert 'line' not in lp_plugin.plot_across_x.layers
        assert not lp_plugin.plot_available

        # Mimic manual GUI inputs.
        lp_plugin.selected_x = 1.1
        lp_plugin.selected_y = 9
        lp_plugin.viewer_selected = 'imviz-0'
        assert lp_plugin.plot_across_x.layers['line'].visible
        assert len(lp_plugin.plot_across_x.layers['line'].layer.data['x']) > 0
        assert len(lp_plugin.plot_across_y.layers['line'].layer.data['x']) > 0
        assert lp_plugin.plot_available

        # Nothing should update on "l" when plugin closed.
        lp_plugin.plugin_opened = False
        lp_plugin._on_viewer_key_event(self.viewer,
                                       {'event': 'keydown', 'key': 'l',
                                        'domain': {'x': 5.1, 'y': 5}})
        lp_plugin.selected_x = 1.1
        lp_plugin.selected_y = 9


def test_line_profile_with_nan(imviz_helper):
    arr = np.ones((10, 10))
    arr[5, 5] = np.nan
    imviz_helper.load_data(arr)

    lp_plugin = imviz_helper.plugins['Imviz Line Profiles (XY)']._obj
    lp_plugin.plugin_opened = True
    lp_plugin.selected_x = 5
    lp_plugin.selected_y = 5
    lp_plugin.vue_draw_plot()
    assert lp_plugin.plot_available

    # NaN still in data but rendered properly as gap.
    # Cannot check the gap stuff in CI but can make sure X-axis is populated properly etc.
    for lp_plot in (lp_plugin.plot_across_x, lp_plugin.plot_across_y):
        assert lp_plot.layers['line'].state.line_visible
        assert not np.all(np.isfinite(lp_plot.layers['line'].layer.data['y']))
        assert_array_equal(lp_plot.layers['line'].layer.data['x'], range(10))
        assert_allclose([lp_plot.layers['line'].state.viewer_state.x_min,
                         lp_plot.layers['line'].state.viewer_state.x_max,
                         lp_plot.layers['line'].state.viewer_state.y_min,
                         lp_plot.layers['line'].state.viewer_state.y_max],
                        [0, 9, 0.95, 1.05])
