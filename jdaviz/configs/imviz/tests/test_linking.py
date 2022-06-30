import pytest
from astropy.table import Table
from glue.core.link_helpers import LinkSame
from glue.plugins.wcs_autolinking.wcs_autolinking import OffsetLink, WCSLink
from numpy.testing import assert_allclose
from regions import PixCoord, CirclePixelRegion

from jdaviz.configs.imviz.helper import get_reference_image_data
from jdaviz.configs.imviz.tests.utils import (
    BaseImviz_WCS_NoWCS, BaseImviz_WCS_WCS, BaseImviz_WCS_GWCS)


class BaseLinkHandler:

    def check_all_pixel_links(self):
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 2
        assert all([isinstance(link, LinkSame) for link in links])

    def test_pixel_linking(self):
        self.imviz.link_data(link_type='pixels', error_on_fail=True)
        self.check_all_pixel_links()


class TestLink_WCS_NoWCS(BaseImviz_WCS_NoWCS, BaseLinkHandler):

    def test_wcslink_fallback_pixels(self):
        self.imviz.link_data(link_type='wcs', error_on_fail=True)
        self.check_all_pixel_links()

        assert self.viewer.get_link_type('has_wcs[SCI,1]') == 'self'
        assert self.viewer.get_link_type('no_wcs[SCI,1]') == 'pixels'

        # Also check the coordinates display: Last loaded is on top.

        self.viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
        assert self.viewer.label_mouseover.value == '+0.00000e+00 '
        assert self.viewer.label_mouseover.world_ra_deg == ''
        assert self.viewer.label_mouseover.world_dec_deg == ''

        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
        assert self.viewer.label_mouseover.value == '+0.00000e+00 '
        assert self.viewer.label_mouseover.world_ra_deg == '337.5202808000'
        assert self.viewer.label_mouseover.world_dec_deg == '-20.8333330600'

    def test_wcslink_nofallback_noerror(self):
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None)
        self.check_all_pixel_links()  # Keeps old links because operation failed silently

    def test_wcslink_nofallback_error(self):
        with pytest.raises(AttributeError, match='pixel_n_dim'):
            self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)


class TestLink_WCS_WCS(BaseImviz_WCS_WCS, BaseLinkHandler):

    def test_wcslink_affine_with_extras(self):
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)
        links = self.imviz.app.data_collection.external_links
        assert len(links) == 1
        assert isinstance(links[0], OffsetLink)

        assert self.viewer.get_link_type('has_wcs_2[SCI,1]') == 'wcs'

        # Customize display on second image (last loaded).
        self.viewer.set_colormap('Viridis')
        self.viewer.stretch = 'sqrt'
        self.viewer.cuts = (0, 100)

        # Add subsets, both interactive and static.
        self.imviz._apply_interactive_region('bqplot:circle', (1.5, 2.5), (3.6, 4.6))
        self.imviz.load_static_regions({
            'my_reg': CirclePixelRegion(center=PixCoord(x=6, y=2), radius=5)})

        # Add markers.
        tbl = Table({'x': (0, 0), 'y': (0, 1)})
        self.viewer.add_markers(tbl, marker_name='xy_markers')
        assert 'xy_markers' in self.imviz.app.data_collection.labels

        # Run linking again, does not matter what kind.
        self.imviz.link_data(link_type='wcs', wcs_fallback_scheme=None, error_on_fail=True)

        # Ensure display is still customized.
        assert self.viewer.state.layers[1].cmap.name == 'viridis'
        assert self.viewer.state.layers[1].stretch == 'sqrt'
        assert_allclose((self.viewer.state.layers[1].v_min, self.viewer.state.layers[1].v_max),
                        (0, 100))

        # Ensure subsets are still there.
        assert 'Subset 1' in self.imviz.get_interactive_regions()
        assert 'my_reg' in [layer.layer.label for layer in self.viewer.state.layers]

        # Ensure markers are deleted.
        # Zoom and pan will reset in this case, so we do not check those.
        assert 'xy_markers' not in self.imviz.app.data_collection.labels
        assert len(self.viewer._marktags) == 0

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

        self.viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=01.0 y=-0.0'
        assert self.viewer.label_mouseover.value == '+1.00000e+00 '
        assert self.viewer.label_mouseover.world_ra_deg == '337.5202808000'
        assert self.viewer.label_mouseover.world_dec_deg == '-20.8333330600'

        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
        assert self.viewer.label_mouseover.value == '+1.00000e+00 '
        assert self.viewer.label_mouseover.world_ra_deg == '337.5202808000'
        assert self.viewer.label_mouseover.world_dec_deg == '-20.8333330600'

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

        self.viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
        assert self.viewer.label_mouseover.value == '+1.00000e+00 '
        assert self.viewer.label_mouseover.world_ra_deg == ''
        assert self.viewer.label_mouseover.world_dec_deg == ''

        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
        assert self.viewer.label_mouseover.value == '+1.00000e+00 electron / s'
        assert self.viewer.label_mouseover.world_ra_deg == '3.5817255823'
        assert self.viewer.label_mouseover.world_dec_deg == '-30.3920580740'

        self.viewer.on_mouse_or_key_event({'event': 'keydown', 'key': 'b',
                                           'domain': {'x': 0, 'y': 0}})
        assert self.viewer.label_mouseover.pixel == 'x=02.7 y=09.8'
        assert self.viewer.label_mouseover.value == ''
        assert self.viewer.label_mouseover.world_ra_deg == '3.5817255823'
        assert self.viewer.label_mouseover.world_dec_deg == '-30.3920580740'


def test_imviz_no_data(imviz_helper):
    with pytest.raises(ValueError, match='No valid reference data'):
        get_reference_image_data(imviz_helper.app)

    imviz_helper.link_data(error_on_fail=True)  # Just no-op, do not crash
    links = imviz_helper.app.data_collection.external_links
    assert len(links) == 0

    with pytest.raises(ValueError, match='No reference data for link look-up'):
        imviz_helper.default_viewer.get_link_type('foo')
