import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from numpy.testing import assert_allclose

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, create_example_gwcs


class TestPanZoomTools(BaseImviz_WCS_WCS):
    def test_panzoom_tools(self):
        v = self.imviz.default_viewer._obj
        v2 = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer('imviz-1', 'has_wcs_1[SCI,1]')

        t = v.toolbar.tools['jdaviz:boxzoommatch']
        # original limits (x_min, x_max, y_min, y_max): -0.5 9.5 -0.5 9.5
        # original limits (zoom_center_x, zoom_center_y, zoom_radius): 4.5 4.5 5.0
        original_limits = v.get_limits()
        assert_allclose(original_limits, (-0.5, 9.5, -0.5, 9.5))
        original_center_rad = (v.state.zoom_center_x, v.state.zoom_center_y, v.state.zoom_radius)
        assert_allclose(original_center_rad, (4.5, 4.5, 5.0))
        assert_allclose(v2.get_limits(), original_limits)
        assert_allclose((v2.state.zoom_center_x, v2.state.zoom_center_y, v2.state.zoom_radius), original_center_rad)  # noqa
        t.activate()
        t.save_prev_zoom()
        v.set_limits(x_min=1, x_max=8, y_min=1, y_max=8)
        # second viewer should match these changes, wrt zoom center and radius
        assert v2.state.zoom_center_x == v.state.zoom_center_x
        assert v2.state.zoom_center_y == v.state.zoom_center_y
        assert v2.state.zoom_radius == v.state.zoom_radius

        v.toolbar.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked (boxzoommatch will re-activate)
        assert_allclose((v.state.zoom_center_x, v.state.zoom_center_y, v.state.zoom_radius), original_center_rad)  # noqa
        assert_allclose((v2.state.zoom_center_x, v2.state.zoom_center_y, v2.state.zoom_radius), original_center_rad)  # noqa

        v.toolbar.tools['jdaviz:prevzoom'].activate()
        # both should revert since they're still linked
        assert v.get_limits() == (1, 8, 1, 8)
        assert v2.get_limits() == (1, 8, 1, 8)

        v.toolbar.tools['jdaviz:boxzoommatch'].deactivate()
        v.toolbar.tools['jdaviz:homezoom'].activate()
        assert_allclose(v.get_limits(), original_limits)
        assert_allclose(v2.get_limits(), (1, 8, 1, 8))
        v.toolbar.tools['jdaviz:prevzoom'].activate()
        assert_allclose(v.get_limits(), (1, 8, 1, 8))
        assert_allclose(v2.get_limits(), (1, 8, 1, 8))
        t.deactivate()

        t_linkedpan = v.toolbar.tools['jdaviz:panzoommatch']
        t_linkedpan.activate()
        v.center_on((0, 0))
        # make sure both viewers moved to the new center
        assert_allclose(v.get_limits(), (-3.5, 3.5, -3.5, 3.5))
        assert_allclose(v2.get_limits(), (-3.5, 3.5, -3.5, 3.5))
        t_linkedpan.deactivate()

        t_normpan = v.toolbar.tools['jdaviz:imagepanzoom']
        t_normpan.activate()
        t_normpan.on_click({'event': 'click', 'domain': {'x': 1, 'y': 1}})
        # make sure only first viewer re-centered since this mode is not linked mode
        assert_allclose(v.get_limits(), (-2.5, 4.5, -2.5, 4.5))
        assert_allclose(v2.get_limits(), (-3.5, 3.5, -3.5, 3.5))
        t_normpan.deactivate()

        t_linkedpan.activate()
        t_linkedpan.on_click({'event': 'click', 'domain': {'x': 2, 'y': 2}})
        # make sure both viewers moved to the new center
        assert_allclose(v.get_limits(), (-1.5, 5.5, -1.5, 5.5))
        assert_allclose(v2.get_limits(), (-1.5, 5.5, -1.5, 5.5))
        t_linkedpan.deactivate()


@pytest.mark.parametrize("align_by", ["Pixels", "WCS"])
def test_panzoom_click_center_linking(imviz_helper, align_by):
    """https://github.com/spacetelescope/jdaviz/issues/2749"""
    v = imviz_helper.default_viewer._obj

    # Since we are not really displaying, need this to test pan/zoom.
    v.shape = (100, 100)
    v.state._set_axes_aspect_ratio(1)

    arr_big = np.ones((40, 30), dtype=int)
    w_big = create_example_gwcs(arr_big.shape)
    arr_small = np.ones((20, 15), dtype=int)
    w_small = create_example_gwcs(arr_small.shape)

    imviz_helper.load_data(NDData(arr_big, wcs=w_big), data_label="big")
    imviz_helper.load_data(NDData(arr_small, wcs=w_small), data_label="small")

    lc_plugin = imviz_helper.plugins['Orientation']
    lc_plugin.align_by = align_by

    coo = SkyCoord(ra=197.89262754541807, dec=-1.3644568140486624, unit="deg")

    if align_by == "WCS":
        mouseover_loc = v.state.reference_data.coords.world_to_pixel(coo)
    else:  # Pixels
        mouseover_loc = w_small.world_to_pixel(coo)

    t = v.toolbar.tools['jdaviz:imagepanzoom']
    t.activate()
    t.on_click({'event': 'click', 'domain': {'x': mouseover_loc[0], 'y': mouseover_loc[1]}})
    t.deactivate()

    # We want to make sure click centers viewer to where it is supposed to be.
    cur_cen = v._get_center_skycoord()
    v.center_on(coo)
    real_cen = v._get_center_skycoord()
    assert_allclose(cur_cen.ra.deg, real_cen.ra.deg)
    assert_allclose(cur_cen.dec.deg, real_cen.dec.deg)


def test_blink(imviz_helper):
    viewer = imviz_helper.default_viewer._obj

    for i in range(3):
        imviz_helper.load_data(np.zeros((2, 2)) + i, data_label=f'image_{i}')

    label_mouseover = imviz_helper.app.session.application._tools['g-coords-info']
    viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b', 'domain': {'x': 0, 'y': 0}})
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00', '', '')
    assert viewer.top_visible_data_label == 'image_0'

    # Blink forward and update coordinates info panel.
    viewer.blink_once()
    assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +1.00000e+00', '', '')
    assert viewer.top_visible_data_label == 'image_1'

    # Blink backward.
    viewer.blink_once(reversed=True)
    assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00', '', '')
    assert viewer.top_visible_data_label == 'image_0'

    # Blink backward again.
    viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'B', 'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +2.00000e+00', '', '')
    assert viewer.top_visible_data_label == 'image_2'


def test_compass_open_while_load(imviz_helper):
    plg = imviz_helper.plugins['Compass']
    plg._obj.plugin_opened = True

    # Should not crash even if Compass is open in tray.
    imviz_helper.load_data(np.ones((2, 2)))
    assert len(imviz_helper.app.data_collection) == 1


def test_tool_visibility(imviz_helper):
    imviz_helper.load_data(np.ones((2, 2)))
    tb = imviz_helper.default_viewer._obj.toolbar

    assert not tb.tools_data['jdaviz:boxzoommatch']['visible']

    assert tb.tools_data['jdaviz:boxzoom']['primary']
    # activate boxzoom to ensure it remains primary
    tb.active_tool_id = 'jdaviz:boxzoom'

    imviz_helper.create_image_viewer()
    imviz_helper.app.set_data_visibility('imviz-1', imviz_helper.app.data_collection[0].label, True)

    assert tb.tools_data['jdaviz:boxzoommatch']['visible']
    assert tb.active_tool_id == 'jdaviz:boxzoom'
    assert tb.tools_data['jdaviz:boxzoom']['primary']

    # but the panzoom has updated primary since there was no active tool in that submenu
    assert tb.tools_data['jdaviz:panzoommatch']['visible']
    assert tb.tools_data['jdaviz:panzoommatch']['primary']

    # now set the tool to the matched box zoom to ensure it deactivates itself when removing
    # a viewer
    tb.active_tool_id = 'jdaviz:boxzoommatch'
    imviz_helper.destroy_viewer('imviz-1')
    assert not tb.tools_data['jdaviz:boxzoommatch']['visible']
    assert tb.active_tool_id is None
