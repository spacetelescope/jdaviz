import numpy as np
from astropy import units as u
from astropy.nddata import NDData
from numpy.testing import assert_allclose

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestLineProfileXY(BaseImviz_WCS_NoWCS):
    def test_plugin_linked_by_pixel(self):
        """Go through plugin logic but does not check plot contents."""
        lp_plugin = self.imviz.app.get_tray_item_from_name('imviz-line-profile-xy')
        lp_plugin.plugin_opened = True

        assert lp_plugin.viewer.labels == ['imviz-0']
        assert lp_plugin.viewer_selected == 'imviz-0'

        # Plot attempt with null X/Y should not crash but also no-op.
        assert len(lp_plugin.plot_across_x.marks['line'].x) == 0
        assert len(lp_plugin.plot_across_y.marks['line'].x) == 0
        lp_plugin.vue_draw_plot()
        assert not lp_plugin.plot_available

        # Mimic "l" key pressed.
        lp_plugin._on_viewer_key_event(self.viewer,
                                       {'event': 'keydown', 'key': 'l',
                                        'domain': {'x': 5.1, 'y': 5}})
        assert_allclose(lp_plugin.selected_x, 5.1)
        assert_allclose(lp_plugin.selected_y, 5)
        assert len(lp_plugin.plot_across_x.marks['line'].x) > 0
        assert len(lp_plugin.plot_across_y.marks['line'].x) > 0
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
        assert len(lp_plugin.plot_across_x.marks['line'].x) > 0
        assert len(lp_plugin.plot_across_y.marks['line'].x) > 0
        assert lp_plugin.plot_available

        # Wrong input resets plots without error.
        lp_plugin.selected_x = -1
        lp_plugin.vue_draw_plot()
        assert len(lp_plugin.plot_across_x.marks['line'].x) == 0
        assert len(lp_plugin.plot_across_y.marks['line'].x) == 0
        assert not lp_plugin.plot_available

        # Mimic manual GUI inputs.
        lp_plugin.selected_x = '1.1'
        lp_plugin.selected_y = '9'
        lp_plugin.viewer_selected = 'imviz-0'
        assert len(lp_plugin.plot_across_x.marks['line'].x) > 0
        assert len(lp_plugin.plot_across_y.marks['line'].x) > 0
        assert lp_plugin.plot_available

        # Nothing should update on "l" when plugin closed.
        lp_plugin.plugin_opened = False
        lp_plugin._on_viewer_key_event(self.viewer,
                                       {'event': 'keydown', 'key': 'l',
                                        'domain': {'x': 5.1, 'y': 5}})
        lp_plugin.selected_x = '1.1'
        lp_plugin.selected_y = '9'
