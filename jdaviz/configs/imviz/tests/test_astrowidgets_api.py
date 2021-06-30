import pytest
from astropy import units as u
from astropy.table import Table
from numpy.testing import assert_allclose

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestCenterOffset(BaseImviz_WCS_NoWCS):

    def test_center_offset_pixel(self):
        self.imviz.center_on((0, 1))
        assert_allclose(self.viewer.state.x_min, -5)
        assert_allclose(self.viewer.state.y_min, -4)
        assert_allclose(self.viewer.state.x_max, 5)
        assert_allclose(self.viewer.state.y_max, 6)

        self.imviz.offset_to(1, -1)
        assert_allclose(self.viewer.state.x_min, -4)
        assert_allclose(self.viewer.state.y_min, -5)
        assert_allclose(self.viewer.state.x_max, 6)
        assert_allclose(self.viewer.state.y_max, 5)

    def test_center_offset_sky(self):
        # Blink to the one with WCS because the last loaded data is shown.
        self.viewer.blink_once()

        sky = self.wcs.pixel_to_world(0, 1)
        self.imviz.center_on(sky)
        assert_allclose(self.viewer.state.x_min, -5)
        assert_allclose(self.viewer.state.y_min, -4)
        assert_allclose(self.viewer.state.x_max, 5)
        assert_allclose(self.viewer.state.y_max, 6)

        dsky = 0.1 * u.arcsec
        self.imviz.offset_to(dsky, dsky, skycoord_offset=True)
        assert_allclose(self.viewer.state.x_min, -5.100000000142565)
        assert_allclose(self.viewer.state.y_min, -3.90000000002971)
        assert_allclose(self.viewer.state.x_max, 4.899999999857435)
        assert_allclose(self.viewer.state.y_max, 6.09999999997029)

        # astropy requires Quantity
        with pytest.raises(u.UnitTypeError):
            self.imviz.offset_to(0.1, 0.1, skycoord_offset=True)

        # Cannot pass Quantity without specifying skycoord_offset=True
        with pytest.raises(u.UnitConversionError):
            self.imviz.offset_to(dsky, dsky)

        # Blink to the one without WCS
        self.viewer.blink_once()

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.center_on(sky)

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.offset_to(dsky, dsky, skycoord_offset=True)


class TestMarkers(BaseImviz_WCS_NoWCS):

    def test_invalid_markers(self):
        with pytest.raises(KeyError, match='Invalid attribute'):
            self.imviz.marker = {'foo': 'bar', 'alpha': 0.8}
        with pytest.raises(ValueError, match='Invalid RGBA argument'):
            self.imviz.marker = {'color': 'greenfishbluefish'}
        with pytest.raises(ValueError, match='Invalid alpha'):
            self.imviz.marker = {'alpha': '1'}
        with pytest.raises(ValueError, match='Invalid alpha'):
            self.imviz.marker = {'alpha': 42}
        with pytest.raises(ValueError, match='Invalid marker size'):
            self.imviz.marker = {'markersize': '1'}

    def test_mvp_markers(self):
        x_pix = (0, 0)
        y_pix = (0, 1)
        sky = self.wcs.pixel_to_world(x_pix, y_pix)
        tbl = Table({'x': x_pix, 'y': y_pix, 'coord': sky})

        self.imviz.add_markers(tbl)
        data = self.imviz.app.data_collection[2]
        assert data.label == 'default-marker-name'
        assert data.style.color == 'red'
        assert data.style.marker == 'o'
        assert_allclose(data.style.markersize, 5)
        assert_allclose(data.style.alpha, 1)
        assert_allclose(data.get_component('x').data, x_pix)
        assert_allclose(data.get_component('y').data, y_pix)

        # Table with only sky coordinates but no use_skycoord=True
        with pytest.raises(KeyError):
            self.imviz.add_markers(tbl[('coord', )])

        # Cannot use reserved marker name
        with pytest.raises(ValueError, match='not allowed'):
            self.imviz.add_markers(tbl, use_skycoord=True, marker_name='all')

        self.imviz.marker = {'color': (0, 1, 0), 'alpha': 0.8}

        self.imviz.add_markers(tbl, use_skycoord=True, marker_name='my_sky')
        data = self.imviz.app.data_collection[3]
        assert data.label == 'my_sky'
        assert data.style.color == (0, 1, 0)  # green
        assert data.style.marker == 'o'
        assert_allclose(data.style.markersize, 3)  # Glue default
        assert_allclose(data.style.alpha, 0.8)
        assert_allclose(data.get_component('ra').data, sky.ra.deg)
        assert_allclose(data.get_component('dec').data, sky.dec.deg)

        # TODO: How to check imviz.app.data_collection.links is correct?
        assert len(self.imviz.app.data_collection.links) == 12

        # Remove markers with default name.
        self.imviz.remove_markers()
        assert self.imviz.app.data_collection.labels == [
            'has_wcs[SCI,1]', 'no_wcs[SCI,1]', 'my_sky']

        # Reset markers (runs remove_markers with marker_name set)
        self.imviz.reset_markers()
        assert self.imviz.app.data_collection.labels == [
            'has_wcs[SCI,1]', 'no_wcs[SCI,1]']

        assert len(self.imviz.app.data_collection.links) == 8

        # NOTE: This changes the state of self.imviz for this test class!

        self.imviz.app.data_collection.remove(self.imviz.app.data_collection[0])
        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.add_markers(tbl, use_skycoord=True, marker_name='my_sky')

        self.imviz.app.data_collection.clear()
        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.imviz.add_markers(tbl, use_skycoord=True, marker_name='my_sky')
