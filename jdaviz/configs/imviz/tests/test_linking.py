import pytest
import numpy as np
from astropy.table import Table
from astropy.wcs import WCS
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import AffineLink, OffsetLink, WCSLink
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

    def check_all_wcs_links(self):
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 3
        assert all([isinstance(link, (AffineLink, OffsetLink)) for link in links])

    def test_pixel_linking(self):
        self.imviz.link_data(align_by='pixels')
        self.check_all_pixel_links()

    @property
    def default_viewer_limits(self):
        return (self.imviz.default_viewer._obj.state.x_min,
                self.imviz.default_viewer._obj.state.x_max,
                self.imviz.default_viewer._obj.state.y_min,
                self.imviz.default_viewer._obj.state.y_max)


class TestLink_WCS_NoWCS(BaseImviz_WCS_NoWCS, BaseLinkHandler):

    def test_wcslink_fallback_pixels(self):
        self.imviz.link_data(align_by='wcs')

        assert self.viewer.get_alignment_method('has_wcs[SCI,1]') == 'wcs'

        # Also check the coordinates display: Last loaded is on top.

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})

        assert label_mouseover.as_text() == (
            'Pixel x=00.3 y=00.2 Value +0.00000e+00',
            'World 22h30m04.8496s -20d49m59.7490s (ICRS)',
            '337.5202064976 -20.8332636155 (deg)'
        )


class TestLink_WCS_FakeWCS(BaseImviz_WCS_NoWCS, BaseLinkHandler):

    def test_badwcs_no_crash(self):
        # There is WCS but it is non-celestial
        self.imviz.app.data_collection[1].coords = WCS(naxis=2)

        self.check_all_pixel_links()

        assert self.viewer.get_alignment_method('has_wcs[SCI,1]') == 'self'
        assert self.viewer.get_alignment_method('no_wcs[SCI,1]') == 'pixels'

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

        self.imviz.link_data(align_by='wcs', wcs_fallback_scheme=None)
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 2
        assert isinstance(links[0], (AffineLink, OffsetLink))
        assert self.viewer.get_alignment_method('has_wcs_2[SCI,1]') == 'wcs'

        # Customize display on second image (last loaded).
        self.viewer.set_colormap('Viridis')
        self.viewer.stretch = 'sqrt'
        self.viewer.cuts = (0, 100)

        # Add subsets, both interactive and static.
        self.imviz._apply_interactive_region('bqplot:truecircle', (1.5, 2.5), (3.6, 4.6))
        self.imviz.plugins['Subset Tools'].combination_mode = 'new'
        self.imviz.plugins['Subset Tools'].import_region([
            CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5).to_sky(self.wcs_1),
            PolygonPixelRegion(vertices=PixCoord(x=[1, 2, 2], y=[1, 1, 2])).to_sky(self.wcs_1),
            PolygonPixelRegion(vertices=PixCoord(x=[2, 3, 3], y=[2, 2, 3])).to_sky(self.wcs_1)])

        # Add markers.
        tbl = Table({'x': (0, 0), 'y': (0, 1)})
        self.viewer.add_markers(tbl, marker_name='xy_markers')
        assert 'xy_markers' in self.imviz.app.data_collection.labels

        # Ensure display is still customized.
        assert self.viewer.state.layers[1].cmap.name == 'viridis'
        assert self.viewer.state.layers[1].stretch == 'sqrt'
        assert_allclose((self.viewer.state.layers[1].v_min, self.viewer.state.layers[1].v_max),
                        (0, 100))

        # Ensure subsets are still there.
        all_labels = [layer.layer.label for layer in self.viewer.state.layers]
        # Retrieved subsets as sky regions from Subset plugin, and ensure they
        # match what was loaded and that they are in sky coordinates.
        subset_as_regions = self.imviz.plugins['Subset Tools'].get_regions()
        assert sorted(subset_as_regions) == ['Subset 1', 'Subset 2']
        assert_allclose(subset_as_regions['Subset 1'].center.ra.deg, 337.519449)
        assert_allclose(subset_as_regions['Subset 2'].center.ra.deg, 337.518498)
        # ensure agreement between app.get_subsets and subset_tools.get_regions
        ss = self.imviz.app.get_subsets(include_sky_region=True)
        assert ss['Subset 1'][0]['sky_region'] == subset_as_regions['Subset 1']
        assert ss['Subset 2'][0]['sky_region'] == subset_as_regions['Subset 2']

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

        # Ensure pan/zoom does not change when markers are not present.
        assert_allclose((self.viewer.state.x_min, self.viewer.state.y_min,
                        self.viewer.state.x_max, self.viewer.state.y_max), ans)

        # Also check the coordinates display: Last loaded is on top.

        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 0, 'y': 0}})

        lmtext = label_mouseover.as_text()
        assert lmtext[0] == 'Pixel x=01.3 y=00.2 Value +1.00000e+00'
        assert lmtext[1:] == ('World 22h30m04.8496s -20d49m59.7490s (ICRS)',
                              '337.5202064976 -20.8332636155 (deg)')

        # blink image through clicking with blink tool
        self.viewer.toolbar.active_tool_id = 'jdaviz:blinkonce'
        self.viewer.toolbar.active_tool.on_click({'event': 'click', 'domain': {'x': 0, 'y': 0}})
        assert label_mouseover.as_text()[0] == 'Pixel x=00.3 y=00.2 Value +1.00000e+00'
        assert label_mouseover.as_text()[1:] == ('World 22h30m04.8496s -20d49m59.7490s (ICRS)',
                                                 '337.5202064976 -20.8332636155 (deg)')

        # Changing link type will raise an error
        with pytest.raises(ValueError, match=".*only be changed after existing subsets are deleted"):  # noqa: E501
            self.imviz.link_data(align_by='pixels', wcs_fallback_scheme=None)

        self.viewer.reset_markers()
        self.imviz.plugins["Orientation"].delete_subsets()
        self.imviz.link_data(align_by='pixels', wcs_fallback_scheme=None)
        assert 'xy_markers' not in self.imviz.app.data_collection.labels
        assert len(self.viewer._marktags) == 0

    def test_wcslink_fullblown(self):
        self.imviz.link_data(align_by='wcs', wcs_fallback_scheme=None,
                             wcs_fast_approximation=False)
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 2
        assert isinstance(links[0], WCSLink)
        assert self.viewer.get_alignment_method('has_wcs_1[SCI,1]') == 'wcs'
        assert self.viewer.get_alignment_method('has_wcs_2[SCI,1]') == 'wcs'

    # Also test other exception handling here.

    def test_invalid_inputs(self):
        with pytest.raises(KeyError):
            self.imviz.link_data(align_by='foo')

        with pytest.raises(ValueError, match='not found in data collection external links'):
            self.viewer.get_alignment_method('foo')


class TestLink_WCS_GWCS(BaseImviz_WCS_GWCS):

    def test_wcslink_rotated(self):
        # FITS WCS will be reference, GWCS is rotated, no_wcs linked by pixel to ref.
        self.imviz.link_data(align_by='wcs')

        # The zoom box for GWCS is now a rotated rombus.
        fits_wcs_zoom_limits = self.viewer._get_zoom_limits(
            self.imviz.app.data_collection['fits_wcs[DATA]'])
        gwcs_zoom_limits = self.viewer._get_zoom_limits(
            self.imviz.app.data_collection['gwcs[DATA]'])

        # x_min, y_min
        # x_min, y_max
        # x_max, y_max
        # x_max, y_min
        assert_allclose(fits_wcs_zoom_limits,
                        [[-2.406711, -1.588057],
                         [-2.697746, 11.137127],
                         [10.148055, 10.554429],
                         [10.439091, -2.170755]], rtol=1e-5)

        # this GWCS has a bounding box, and outside of the bounding box will
        # return nans:
        assert_allclose(gwcs_zoom_limits, np.nan)

        # Also check the coordinates display: Last loaded is on top.
        # Cycle order: GWCS, FITS WCS
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        xy = self.viewer._get_real_xy(self.imviz.app.data_collection[0], 0, 0, reverse=True)
        label_mouseover._viewer_mouse_event(
            self.viewer, {'event': 'mousemove', 'domain': {'x': xy[0], 'y': xy[1]}})
        assert label_mouseover.as_text() == ('Pixel x=02.7 y=09.8',
                                             'World 00h14m19.6141s -30d23m31.4091s (ICRS)',
                                             '3.5817255823 -30.3920580740 (deg)')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        # Make sure GWCS does not extrapolate.
        xy = self.viewer._get_real_xy(self.imviz.app.data_collection[1], -1, -1, reverse=True)
        label_mouseover._viewer_mouse_event(
            self.viewer, {'event': 'mousemove', 'domain': {'x': xy[0], 'y': xy[1]}})
        assert label_mouseover.as_text() == ('Pixel', '', '')
        # FITS WCS is reference data and has no concept of bounding box
        # but cursor is outside GWCS bounding box
        assert label_mouseover.row1_unreliable
        assert label_mouseover.row3_unreliable

        # row2 was "unreliable" when the WCS-only layer used GWCS.
        # now with FITS WCS as the coordinate frame, there is no bounding
        # box and row2 is reliable.
        assert not label_mouseover.row2_unreliable

        xy = self.viewer._get_real_xy(self.imviz.app.data_collection[0], 0, 0, reverse=True)
        self.viewer.blink_once()
        label_mouseover._viewer_mouse_event(
            self.viewer, {'event': 'mousemove', 'domain': {'x': xy[0], 'y': xy[1]}})
        assert label_mouseover.as_text()[0] in (
            'Pixel x=00.0 y=00.0 Value +1.00000e+00 electron / s',
            'Pixel x=-0.0 y=00.0 Value +1.00000e+00 electron / s',
            'Pixel x=00.0 y=-0.0 Value +1.00000e+00 electron / s',
            'Pixel x=-0.0 y=-0.0 Value +1.00000e+00 electron / s'
        )
        assert label_mouseover.as_text()[1:] == ('World 00h14m19.6141s -30d23m31.4091s (ICRS)',
                                                 '3.5817255823 -30.3920580740 (deg)')
        assert not label_mouseover.row1_unreliable
        assert not label_mouseover.row2_unreliable
        assert not label_mouseover.row3_unreliable

        # Regression test for https://github.com/spacetelescope/jdaviz/issues/2079 to
        # make sure this does not crash.
        viewer2 = self.imviz.create_image_viewer(viewer_name='second')
        viewer2.state.reset_limits()


class TestLink_GWCS_GWCS(BaseImviz_GWCS_GWCS):

    def test_pixel_linking(self):
        self.imviz.link_data(align_by='pixels')

        # Check the coordinates display: Last loaded is on top.
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove', 'domain': {'x': -1, 'y': -1}})

        # do not display world coordinates outside of the bounding box
        assert label_mouseover.as_text() == ('Pixel x=-1.0 y=-1.0', '', '')
        assert not label_mouseover.row1_unreliable
        assert label_mouseover.row3_unreliable

        # `row2_unreliable` was True when the WCS-only layer used GWCS.
        # now with FITS WCS as the coordinate frame, there is no bounding
        # box and row2 is reliable.
        assert not label_mouseover.row2_unreliable

        # Back to reference image with bounds check.
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'keydown', 'key': 'b',
                                             'domain': {'x': -1, 'y': -1}})
        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': -1, 'y': -1}})

        # do not display world coordinates outside of the bounding box
        assert label_mouseover.as_text() == ('Pixel x=-1.0 y=-1.0', '', '')
        assert not label_mouseover.row1_unreliable
        assert label_mouseover.row3_unreliable

        # row2 was "unreliable" when the WCS-only layer used GWCS.
        # now with FITS WCS as the coordinate frame, there is no bounding
        # box and row2 is reliable.
        assert not label_mouseover.row2_unreliable


def test_imviz_no_data(imviz_helper):
    refdata, iref = get_reference_image_data(imviz_helper.app)
    assert refdata is None
    assert iref == -1

    imviz_helper.link_data()  # Just no-op, do not crash
    links = imviz_helper.app.data_collection.external_links
    assert len(links) == 0

    with pytest.raises(ValueError, match='No reference data for link look-up'):
        imviz_helper.default_viewer._obj.get_alignment_method('foo')
