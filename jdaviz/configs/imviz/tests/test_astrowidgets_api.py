import os

import asdf
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from astropy.table import Table
from astropy.utils.data import get_pkg_data_filename
from astropy.visualization import AsinhStretch, LinearStretch, LogStretch, SqrtStretch
from numpy.testing import assert_allclose

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS, BaseImviz_WCS_WCS


# TODO: Remove skip when https://github.com/bqplot/bqplot/pull/1397/files#r726500097 is resolved.
@pytest.mark.skip(reason="Cannot test due to async JS callback")
class TestSave(BaseImviz_WCS_NoWCS):

    def test_save(self, tmpdir):
        filename = os.path.join(tmpdir.strpath, 'myimage')
        self.viewer.save(filename)

        # This only tests that something saved, not the content.
        assert os.path.isfile(f'{filename}.png')


class TestCenterOffset(BaseImviz_WCS_NoWCS):

    def test_center_offset_pixel(self):
        self.viewer.center_on((0, 1))
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-5, 5, -4, 6))

        self.viewer.offset_by(1 * u.pix, -1 * u.dimensionless_unscaled)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-4, 6, -5, 5))

        self.viewer.offset_by(1, 0)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-3, 7, -5, 5))

        # Out-of-bounds centering is now allowed because it is needed
        # for dithering use case.
        self.viewer.center_on((-1, 99999))
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-6, 4, 9.99940e+04, 1.00004e+05))

        # Sometimes invalid WCS also gives such output, should be no-op
        self.viewer.center_on((np.array(np.nan), np.array(np.nan)))
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-6, 4, 9.99940e+04, 1.00004e+05))

    def test_center_offset_sky(self):
        # Blink to the one with WCS because the last loaded data is shown.
        self.viewer.blink_once()

        sky = self.wcs.pixel_to_world(0, 1)
        self.viewer.center_on(sky)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-5, 5, -4, 6))

        dsky = 0.1 * u.arcsec
        self.viewer.offset_by(-dsky, dsky)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-4.9, 5.1, -3.90000000002971, 6.09999999997029))

        # Cannot mix pixel with sky
        with pytest.raises(ValueError, match='but dy is of type'):
            self.viewer.offset_by(0.1, dsky)

        # Cannot pass invalid Quantity
        with pytest.raises(u.UnitTypeError):
            self.viewer.offset_by(dsky, 1 * u.AA)
        with pytest.raises(u.UnitTypeError):
            self.viewer.offset_by(1 * u.AA, dsky)

        # Blink to the one without WCS
        self.viewer.blink_once()

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.viewer.center_on(sky)

        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.viewer.offset_by(dsky, dsky)


class TestCenter(BaseImviz_WCS_WCS):

    def test_center_on_pix(self):
        self.imviz.link_data(link_type='wcs', error_on_fail=True)

        # This is the second loaded data that is dithered by 1-pix.
        self.viewer.center_on((0, 0))
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-6, 4, -5, 5))

        # This is the first data.
        self.viewer.blink_once()
        self.viewer.center_on((0, 0))
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-5, 5, -5, 5))

        # Centering by sky on second data.
        self.viewer.blink_once()
        sky = self.wcs_2.pixel_to_world(0, 0)
        self.viewer.center_on(sky)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (-6, 4, -5, 5))


class TestZoom(BaseImviz_WCS_NoWCS):

    @pytest.mark.parametrize('val', (0, -0.1, 'foo', [1, 2]))
    def test_invalid_zoom_level(self, val):
        with pytest.raises(ValueError, match='Unsupported zoom level'):
            self.viewer.zoom_level = val

    def test_invalid_zoom(self):
        with pytest.raises(ValueError, match='zoom only accepts int or float'):
            self.viewer.zoom('fit')

    def assert_zoom_results(self, zoom_level, x_min, x_max, y_min, y_max, dpix):
        assert_allclose(self.viewer.zoom_level, zoom_level)
        assert_allclose((self.viewer.state.x_min, self.viewer.state.x_max,
                         self.viewer.state.y_min, self.viewer.state.y_max),
                        (x_min + dpix, x_max + dpix,
                         y_min + dpix, y_max + dpix))

    @pytest.mark.parametrize('is_offcenter', (False, True))
    def test_zoom(self, is_offcenter):
        if is_offcenter:
            self.viewer.center_on((0, 0))
            dpix = -4.5
        else:
            self.viewer.center_on((4.5, 4.5))
            dpix = 0

        self.assert_zoom_results(10, -0.5, 9.5, -0.5, 9.5, dpix)

        # NOTE: Not sure why X/Y min/max not exactly the same as aspect ratio 1
        self.viewer.zoom_level = 1
        self.assert_zoom_results(1, -46, 54, -45.5, 54.5, dpix)

        self.viewer.zoom_level = 2
        self.assert_zoom_results(2, -21.5, 28.5, -20.5, 29.5, dpix)

        self.viewer.zoom(2)
        self.assert_zoom_results(4, -9.5, 15.5, -8.0, 17.0, dpix)

        self.viewer.zoom(0.5)
        self.assert_zoom_results(2, -22.5, 27.5, -20.5, 29.5, dpix)

        self.viewer.zoom_level = 0.5
        self.assert_zoom_results(0.5, -98, 102, -95.5, 104.5, dpix)

        # This fits the whole image on screen, regardless.
        # NOTE: But somehow Y min/max auto-adjust does not work properly
        # in the unit test when off-center. Works in notebook though.
        if not is_offcenter:
            self.viewer.zoom_level = 'fit'
            self.assert_zoom_results(10, -0.5, 9.5, -0.5, 9.5, 0)


class TestCmapStretchCuts(BaseImviz_WCS_NoWCS):

    def test_colormap_options(self):
        assert self.viewer.colormap_options == [
            'Gray', 'Viridis', 'Plasma', 'Inferno', 'Magma', 'Purple-Blue',
            'Yellow-Green-Blue', 'Yellow-Orange-Red', 'Red-Purple', 'Blue-Green',
            'Hot', 'Red-Blue', 'Red-Yellow-Blue', 'Purple-Orange', 'Purple-Green',
            'Rainbow', 'Seismic',
            'Reversed: Gray', 'Reversed: Viridis', 'Reversed: Plasma', 'Reversed: Inferno',
            'Reversed: Magma', 'Reversed: Hot', 'Reversed: Rainbow']

    def test_invalid_colormap(self):
        with pytest.raises(ValueError, match='Invalid colormap'):
            self.viewer.set_colormap('foo')

    def test_stretch_options(self):
        assert self.viewer.stretch_options == ['arcsinh', 'linear', 'log', 'sqrt']

    @pytest.mark.parametrize(('vizclass', 'ans'),
                             [(AsinhStretch, 'arcsinh'),
                              (LinearStretch, 'linear'),
                              (LogStretch, 'log'),
                              (SqrtStretch, 'sqrt')])
    def test_stretch_astropy(self, vizclass, ans):
        self.viewer.stretch = vizclass
        assert self.viewer.stretch == ans

    def test_invalid_stretch(self):
        class FakeStretch:
            pass

        with pytest.raises(ValueError, match='Invalid stretch'):
            self.viewer.stretch = FakeStretch

        with pytest.raises(ValueError, match='Invalid stretch'):
            self.viewer.stretch = 'foo'

    def test_autocut_options(self):
        assert self.viewer.autocut_options == ['minmax', '99.5%', '99%', '95%', '90%']

    @pytest.mark.parametrize(('auto_option', 'ans'),
                             [('minmax', (0, 99)),
                              ('99.5%', (0.2475, 98.7525)),
                              ('99%', (0.495, 98.505)),
                              ('95%', (2.475, 96.525)),
                              ('90%', (4.95, 94.05))])
    def test_autocut(self, auto_option, ans):
        self.viewer.cuts = auto_option
        assert_allclose(self.viewer.cuts, ans)

    def test_invalid_autocut(self):
        with pytest.raises(ValueError, match='Invalid autocut'):
            self.viewer.cuts = 'foo'

    @pytest.mark.parametrize('val', [99, (1, ), (1, 2, 3), (1, 'foo')])
    def test_invalid_cuts(self, val):
        with pytest.raises(ValueError, match='Invalid cut levels'):
            self.viewer.cuts = val

    def test_cmap_stretch_cuts(self):
        # Change colormap, stretch, and cuts on one image
        self.viewer.set_colormap('Viridis')
        self.viewer.stretch = 'sqrt'
        self.viewer.cuts = '95%'

        self.viewer.blink_once()

        # Change colormap, stretch, and cuts on other image
        self.viewer.set_colormap('Red-Yellow-Blue')
        self.viewer.stretch = AsinhStretch
        self.viewer.cuts = (0, 100)

        # Make sure settings stick on both images, second image displayed/changed first above.
        assert self.viewer.state.layers[0].cmap.name == 'RdYlBu'  # matplotlib name, not Glue
        assert self.viewer.state.layers[0].stretch == 'arcsinh'
        assert_allclose((self.viewer.state.layers[0].v_min, self.viewer.state.layers[0].v_max),
                        (0, 100))

        assert self.viewer.state.layers[1].cmap.name == 'viridis'  # matplotlib name, not Glue
        assert self.viewer.state.layers[1].stretch == 'sqrt'
        assert_allclose((self.viewer.state.layers[1].v_min, self.viewer.state.layers[1].v_max),
                        (2.475, 96.525))

        # Go back to initial image for other tests.
        self.viewer.blink_once()


class TestMarkers(BaseImviz_WCS_NoWCS):

    def test_invalid_markers(self):
        with pytest.raises(KeyError, match='Invalid attribute'):
            self.viewer.marker = {'foo': 'bar', 'alpha': 0.8}
        with pytest.raises(ValueError, match='Invalid RGBA argument'):
            self.viewer.marker = {'color': 'greenfishbluefish'}
        with pytest.raises(ValueError, match='Invalid alpha'):
            self.viewer.marker = {'alpha': '1'}
        with pytest.raises(ValueError, match='Invalid alpha'):
            self.viewer.marker = {'alpha': 42}
        with pytest.raises(ValueError, match='Invalid marker size'):
            self.viewer.marker = {'markersize': '1'}
        with pytest.raises(ValueError, match='Invalid fill'):
            self.viewer.marker = {'fill': '1'}

    def test_mvp_markers(self):
        x_pix = (0, 0)
        y_pix = (0, 1)
        sky = self.wcs.pixel_to_world(x_pix, y_pix)
        tbl = Table({'x': x_pix, 'y': y_pix, 'coord': sky})

        self.viewer.add_markers(tbl)
        data = self.imviz.app.data_collection[2]
        assert data.label == 'default-marker-name'
        assert data.style.color == '#ff0000'  # Converted to hex now but still red
        assert data.style.marker == 'o'
        assert_allclose(data.style.markersize, 5)
        assert_allclose(data.style.alpha, 1)
        assert_allclose(data.get_component('x').data, x_pix)
        assert_allclose(data.get_component('y').data, y_pix)
        assert self.viewer.layers[2].layer.label == data.label
        assert self.viewer.layers[2].state.fill is True

        # Table with only sky coordinates but no use_skycoord=True
        with pytest.raises(KeyError):
            self.viewer.add_markers(tbl[('coord', )])

        # Cannot use reserved marker name
        with pytest.raises(ValueError, match='not allowed'):
            self.viewer.add_markers(tbl, use_skycoord=True, marker_name='all')

        self.viewer.marker = {'color': (0, 1, 0), 'alpha': 0.8, 'fill': False}

        self.viewer.add_markers(tbl, use_skycoord=True, marker_name='my_sky')
        data = self.imviz.app.data_collection[3]
        assert data.label == 'my_sky'
        assert data.style.color == '#00ff00'  # Converted to hex now but still green
        assert data.style.marker == 'o'
        assert_allclose(data.style.markersize, 3)  # Glue default
        assert_allclose(data.style.alpha, 0.8)
        assert_allclose(data.get_component('ra').data, sky.ra.deg)
        assert_allclose(data.get_component('dec').data, sky.dec.deg)
        assert self.viewer.layers[3].layer.label == data.label
        assert self.viewer.layers[3].state.fill is False

        # Make sure the other marker is not changed.
        assert self.imviz.app.data_collection[2].style.color == '#ff0000'
        assert self.viewer.layers[2].state.fill is True

        # TODO: How to check imviz.app.data_collection.links is correct?
        assert len(self.imviz.app.data_collection.links) == 14

        # Just want to make sure nothing crashes. Zooming already testing elsewhere.
        # https://github.com/spacetelescope/jdaviz/pull/1971
        self.viewer.zoom_level = 'fit'

        # Remove markers with default name.
        self.viewer.remove_markers()
        assert self.imviz.app.data_collection.labels == [
            'has_wcs[SCI,1]', 'no_wcs[SCI,1]', 'my_sky']

        # Reset markers (runs remove_markers with marker_name set)
        self.viewer.reset_markers()
        assert self.imviz.app.data_collection.labels == [
            'has_wcs[SCI,1]', 'no_wcs[SCI,1]']

        assert len(self.imviz.app.data_collection.links) == 10

        # NOTE: This changes the state of self.imviz for this test class!

        self.imviz.app.data_collection.remove(self.imviz.app.data_collection[0])
        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.viewer.add_markers(tbl, use_skycoord=True, marker_name='my_sky')

        self.imviz.app.data_collection.clear()
        with pytest.raises(AttributeError, match='does not have a valid WCS'):
            self.viewer.add_markers(tbl, use_skycoord=True, marker_name='my_sky')


def test_markers_gwcs_lonlat(imviz_helper):
    """GWCS uses Lon/Lat for ICRS."""
    gw_file = get_pkg_data_filename('data/miri_i2d_lonlat_gwcs.asdf')
    with asdf.open(gw_file) as af:
        gw = af.tree['wcs']
    ndd = NDData(np.ones((10, 10), dtype=np.float32), wcs=gw, unit='MJy/sr')
    imviz_helper.load_data(ndd, data_label='MIRI_i2d')
    assert imviz_helper.app.data_collection[0].label == 'MIRI_i2d[DATA]'
    assert imviz_helper.app.data_collection[0].components == [
        'Pixel Axis 0 [y]', 'Pixel Axis 1 [x]', 'Lat', 'Lon', 'DATA']

    # If you run this interactively, should appear slightly off-center.
    calib_cat = Table({'coord': [SkyCoord(80.6609, -69.4524, unit='deg')]})
    imviz_helper.default_viewer.add_markers(calib_cat, use_skycoord=True, marker_name='my_sky')
    assert imviz_helper.app.data_collection[1].label == 'my_sky'
