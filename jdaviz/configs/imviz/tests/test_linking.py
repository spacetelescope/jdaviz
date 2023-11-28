import pytest
from astropy.table import Table
from astropy.wcs import WCS
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import OffsetLink, WCSLink
from numpy.testing import assert_allclose
from regions import PixCoord, CirclePixelRegion, PolygonPixelRegion

from jdaviz.configs.imviz.helper import get_reference_image_data
from jdaviz.configs.imviz.tests.utils import (
    BaseImviz_WCS_NoWCS, BaseImviz_WCS_WCS, BaseImviz_WCS_GWCS, BaseImviz_GWCS_GWCS)


class BaseLinkHandler:

    def check_all_pixel_links(self):
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 2
        assert all([isinstance(link, LinkSame) for link in links])

    def test_pixel_linking(self):
        self.imviz.link_data(link_type='pixels', error_on_fail=True)
        self.check_all_pixel_links()

    @property
    def default_viewer_limits(self):
        return (self.imviz.default_viewer._obj.state.x_min,
                self.imviz.default_viewer._obj.state.x_max,
                self.imviz.default_viewer._obj.state.y_min,
                self.imviz.default_viewer._obj.state.y_max)


class TestLink_WCS_NoWCS(BaseImviz_WCS_NoWCS, BaseLinkHandler):

    def test_wcslink_fallback_pixels(self):
        self.imviz.link_data(link_type='wcs', error_on_fail=True)
        self.check_all_pixel_links()

        assert self.viewer.get_link_type('has_wcs[SCI,1]') == 'self'
        assert self.viewer.get_link_type('no_wcs[SCI,1]') == 'pixels'

        # Also check the coordinates display: Last loaded is on top.

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00', '', '')

        # blink image through keypress
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00',
                                             'World 22h30m04.8674s -20d49m59.9990s (ICRS)',
                                             '337.5202808000 -20.8333330600 (deg)')

    def test_wcslink_nofallback_noerror(self):
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None)
        self.check_all_pixel_links()  # Keeps old links because operation failed silently

    def test_wcslink_nofallback_error(self):
        with pytest.raises(AttributeError, match='pixel_n_dim'):
            self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)


class TestLink_WCS_FakeWCS(BaseImviz_WCS_NoWCS, BaseLinkHandler):

    def test_badwcs_no_crash(self):
        # There is WCS but it is non-celestial
        self.imviz.app.data_collection[1].coords = WCS(naxis=2)

        self.check_all_pixel_links()

        assert self.viewer.get_link_type('has_wcs[SCI,1]') == 'self'
        assert self.viewer.get_link_type('no_wcs[SCI,1]') == 'pixels'

        # Also check the coordinates display: Last loaded is on top.

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00', '', '')

        # blink image through keypress
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +0.00000e+00',
                                             'World 22h30m04.8674s -20d49m59.9990s (ICRS)',
                                             '337.5202808000 -20.8333330600 (deg)')


class TestLink_WCS_WCS(BaseImviz_WCS_WCS, BaseLinkHandler):

    def test_wcslink_affine_with_extras(self):
        orig_pixel_limits = self.default_viewer_limits
        assert_allclose(orig_pixel_limits, (-0.5, 9.5, -0.5, 9.5))

        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 1
        assert isinstance(links[0], OffsetLink)

        assert self.viewer.get_link_type('has_wcs_2[SCI,1]') == 'wcs'

        # linking should not change axes limits, but should when resetting
        assert_allclose(self.default_viewer_limits, orig_pixel_limits)
        self.imviz.default_viewer.reset_limits()
        assert_allclose(self.default_viewer_limits, (-1.5, 9.5, -1, 10))

        # Customize display on second image (last loaded).
        self.viewer.set_colormap('Viridis')
        self.viewer.stretch = 'sqrt'
        self.viewer.cuts = (0, 100)

        # Add subsets, both interactive and static.
        self.imviz._apply_interactive_region('bqplot:truecircle', (1.5, 2.5), (3.6, 4.6))
        self.imviz.load_regions([CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5),
                                 PolygonPixelRegion(vertices=PixCoord(x=[1, 2, 2], y=[1, 1, 2])),
                                 PolygonPixelRegion(vertices=PixCoord(x=[2, 3, 3], y=[2, 2, 3]))])

        # Add markers.
        tbl = Table({'x': (0, 0), 'y': (0, 1)})
        self.viewer.add_markers(tbl, marker_name='xy_markers')
        assert 'xy_markers' in self.imviz.app.data_collection.labels

        # Run linking again with the same options as before (otherwise would fail with an error
        # since markers now exist)
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)

        # Ensure display is still customized.
        assert self.viewer.state.layers[1].cmap.name == 'viridis'
        assert self.viewer.state.layers[1].stretch == 'sqrt'
        assert_allclose((self.viewer.state.layers[1].v_min, self.viewer.state.layers[1].v_max),
                        (0, 100))

        # Ensure subsets are still there.
        all_labels = [layer.layer.label for layer in self.viewer.state.layers]
        assert sorted(self.imviz.get_interactive_regions()) == ['Subset 1', 'Subset 2']
        assert 'MaskedSubset 1' in all_labels
        assert 'MaskedSubset 2' in all_labels

        # Markers should still exist since the type has not changed
        # Zoom and pan will reset in this case, so we do not check those.
        assert 'xy_markers' in self.imviz.app.data_collection.labels
        assert len(self.viewer._marktags) == 1

        # Pan/zoom.
        self.viewer.center_on((5, 5))
        self.viewer.zoom_level = 0.789
        ans = (self.viewer.state.x_min, self.viewer.state.y_min,
               self.viewer.state.x_max, self.viewer.state.y_max)

        # Run linking again, does not matter what kind.
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)

        # Ensure pan/zoom does not change when markers are not present.
        assert_allclose((self.viewer.state.x_min, self.viewer.state.y_min,
                        self.viewer.state.x_max, self.viewer.state.y_max), ans)

        # Also check the coordinates display: Last loaded is on top.

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 0, 'y': 0}})

        lmtext = label_mouseover.as_text()
        assert lmtext[0] in ('Pixel x=01.0 y=00.0 Value +1.00000e+00',
                             'Pixel x=01.0 y=-0.0 Value +1.00000e+00')
        assert lmtext[1:] == ('World 22h30m04.8674s -20d49m59.9990s (ICRS)',
                              '337.5202808000 -20.8333330600 (deg)')

        # blink image through clicking with blink tool
        self.viewer.toolbar.active_tool_id = 'jdaviz:blinkonce'
        self.viewer.toolbar.active_tool.on_click({'event': 'click', 'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +1.00000e+00',
                                             'World 22h30m04.8674s -20d49m59.9990s (ICRS)',
                                             '337.5202808000 -20.8333330600 (deg)')

        # Changing link type will raise an error
        with pytest.raises(ValueError, match="cannot change link_type"):
            self.imviz.link_data(link_type='pixels', wcs_fallback_scheme=None, error_on_fail=True)

        self.viewer.reset_markers()
        self.imviz.link_data(link_type='pixels', wcs_fallback_scheme=None, error_on_fail=True)
        assert 'xy_markers' not in self.imviz.app.data_collection.labels
        assert len(self.viewer._marktags) == 0

    def test_wcslink_fullblown(self):
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, wcs_use_affine=False,
                             error_on_fail=True)
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 1
        assert isinstance(links[0], WCSLink)
        assert self.viewer.get_link_type('has_wcs_1[SCI,1]') == 'self'
        assert self.viewer.get_link_type('has_wcs_2[SCI,1]') == 'wcs'

    # Also test other exception handling here.

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match='link_type'):
            self.imviz.link_data(link_type='foo')

        with pytest.raises(ValueError, match='wcs_fallback_scheme'):
            self.imviz.link_data(link_type='wcs', wcs_fallback_scheme='foo')

        with pytest.raises(ValueError, match='not found in data collection external links'):
            self.viewer.get_link_type('foo')


class TestLink_WCS_GWCS(BaseImviz_WCS_GWCS):

    def test_wcslink_rotated(self):
        # FITS WCS will be reference, GWCS is rotated, no_wcs linked by pixel to ref.
        self.imviz.link_data(link_type='wcs', error_on_fail=True)

        # The zoom box for GWCS is now a rotated rombus.
        fits_wcs_zoom_limits = self.viewer._get_zoom_limits(
            self.imviz.app.data_collection['fits_wcs[DATA]'])
        gwcs_zoom_limits = self.viewer._get_zoom_limits(
            self.imviz.app.data_collection['gwcs[DATA]'])
        no_wcs_zoom_limits = self.viewer._get_zoom_limits(
            self.imviz.app.data_collection['no_wcs'])
        assert_allclose(fits_wcs_zoom_limits,
                        ((-0.972136, 0.027864), (-0.972136, 8.972136),
                         (7.972136, 8.972136), (7.972136, 0.027864)), rtol=1e-5)
        assert_allclose(gwcs_zoom_limits,
                        ((3.245117, 10.549265), (10.688389, 4.95208),
                         (6.100057, -2.357782), (-1.343215, 3.239403)), rtol=1e-5)
        assert_allclose(no_wcs_zoom_limits, fits_wcs_zoom_limits)

        # Also check the coordinates display: Last loaded is on top.
        # Cycle order: no_wcs, FITS WCS, GWCS

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +1.00000e+00', '', '')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +1.00000e+00 electron / s',
                                             'World 00h14m19.6141s -30d23m31.4091s (ICRS)',
                                             '3.5817255823 -30.3920580740 (deg)')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        # viewer, not label_mouseover event
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=02.7 y=09.8',
                                             'World 00h14m19.6141s -30d23m31.4091s (ICRS)',
                                             '3.5817255823 -30.3920580740 (deg)')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        # Make sure GWCS now can extrapolate. Domain x,y is for FITS WCS data
        # but they are linked by WCS.
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 11.281551269520731,
                                                        'y': 2.480347927198246}})
        assert label_mouseover.as_text() == ('Pixel x=-1.0 y=-1.0',
                                             'World 00h14m19.5829s -30d23m30.9860s (ICRS)',
                                             '3.5815955408 -30.3919405616 (deg)')
        # FITS WCS is reference data and has no concept of bounding box
        # but cursor is outside GWCS bounding box
        assert label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable


class TestLink_GWCS_GWCS(BaseImviz_GWCS_GWCS):
    def test_wcslink_offset(self):
        self.imviz.link_data(link_type='wcs', error_on_fail=True)

        # Check the coordinates display: Last loaded is on top.
        # Within bounds of non-reference image but out of bounds of reference image.
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 10, 'y': 3}})
        lmtext = label_mouseover.as_text()
        assert lmtext[0] in ('Pixel x=07.0 y=00.0 Value +0.00000e+00',
                             'Pixel x=07.0 y=-0.0 Value +0.00000e+00')
        assert lmtext[1:] == ('World 00h14m19.6291s -30d23m30.9692s (ICRS)',
                              '3.5817877198 -30.3919358920 (deg)')

        assert label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable

        # Non-reference image out of bounds of its own bounds but not of the
        # reference image's bounds. Head hurting yet?
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 0.5, 'y': 0.5}})
        assert label_mouseover.as_text() == ('Pixel x=-2.5 y=-2.5',
                                             'World 00h14m19.5908s -30d23m31.0272s (ICRS)',
                                             '3.5816283341 -30.3919519949 (deg)')
        assert label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable

        # Back to reference image
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'keydown', 'key': 'b',
                                             'domain': {'x': 0, 'y': 0}})
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +1.00000e+00 electron / s',
                                             'World 00h14m19.5882s -30d23m31.0135s (ICRS)',
                                             '3.5816174030 -30.3919481838 (deg)')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        # Still reference image but outside its own bounds.
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 10, 'y': 3}})
        assert label_mouseover.as_text() == ('Pixel x=10.0 y=03.0',
                                             'World 00h14m19.6291s -30d23m30.9692s (ICRS)',
                                             '3.5817877198 -30.3919358920 (deg)')
        assert not label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable

        # Regression test for https://github.com/spacetelescope/jdaviz/issues/2079 to
        # make sure this does not crash.
        viewer2 = self.imviz.create_image_viewer(viewer_name='second')
        viewer2.state.reset_limits()

    def test_pixel_linking(self):
        self.imviz.link_data(link_type='pixels')

        # Check the coordinates display: Last loaded is on top.
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': -1, 'y': -1}})
        assert label_mouseover.as_text() == ('Pixel x=-1.0 y=-1.0',
                                             'World 00h14m19.5987s -30d23m31.0683s (ICRS)',
                                             '3.5816611274 -30.3919634282 (deg)')
        assert not label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable

        # Back to reference image with bounds check.
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'keydown', 'key': 'b',
                                             'domain': {'x': -1, 'y': -1}})
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': -1, 'y': -1}})
        assert label_mouseover.as_text() == ('Pixel x=-1.0 y=-1.0',
                                             'World 00h14m19.5829s -30d23m30.9860s (ICRS)',
                                             '3.5815955408 -30.3919405616 (deg)')
        assert not label_mouseover.row1_unreliable
        assert label_mouseover.row2_unreliable
        assert label_mouseover.row3_unreliable


def test_imviz_no_data(imviz_helper):
    with pytest.raises(ValueError, match='No valid reference data'):
        get_reference_image_data(imviz_helper.app)

    imviz_helper.link_data(error_on_fail=True)  # Just no-op, do not crash
    links = imviz_helper.app.data_collection.external_links
    assert len(links) == 0

    with pytest.raises(ValueError, match='No reference data for link look-up'):
        imviz_helper.default_viewer._obj.get_link_type('foo')
