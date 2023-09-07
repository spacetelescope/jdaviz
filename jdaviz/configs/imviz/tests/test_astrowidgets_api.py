import os

import asdf
import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from astropy.utils.data import get_pkg_data_filename
from astropy.utils.exceptions import AstropyUserWarning
from astropy.visualization import AsinhStretch, LinearStretch, LogStretch, SqrtStretch
from numpy.testing import assert_allclose
from regions import (PixCoord, CirclePixelRegion, CircleSkyRegion, PolygonPixelRegion,
                     RectanglePixelRegion, TextPixelRegion)

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
        with pytest.raises(KeyError, match='Invalid attribute'):
            self.viewer.marker = {'markersize': '1'}
        with pytest.raises(ValueError, match='Invalid fill'):
            self.viewer.marker = {'fill': '1'}

    def test_mvp_markers(self):
        reg_pix = CirclePixelRegion(PixCoord(0, 1), 3)
        reg_sky = reg_pix.to_sky(self.wcs)

        # No markers yet but this should not crash.
        for marker_name in (None, "foo"):
            out_regs = self.viewer.get_markers(marker_name=marker_name)
        assert out_regs.regions == []

        self.viewer.add_markers([reg_pix])
        bqplot_marks = self.viewer._get_marks(self.viewer._default_mark_tag_name)
        assert len(bqplot_marks) == 1
        assert len(self.imviz.app.data_collection) == 2  # No new data added
        assert self.viewer._default_mark_tag_name in self.viewer._marker_regions
        assert bqplot_marks[0].visible
        assert bqplot_marks[0].colors == ["red"]
        assert bqplot_marks[0].opacities == [1]
        assert bqplot_marks[0].fill_opacities == [0]

        with pytest.raises(TypeError, match="Markers cannot accept"):
            self.viewer.add_markers(self.wcs)

        # Cannot use reserved marker name
        with pytest.raises(ValueError, match="not allowed"):
            self.viewer.add_markers(reg_pix, marker_name="all")

        self.viewer.marker = {"color": "#00ff00", "alpha": 0.8, "fill": True}
        self.viewer.add_markers(reg_sky, marker_name="my_sky")
        bqplot_marks = self.viewer._get_marks("my_sky")
        assert len(bqplot_marks) == 1
        assert "my_sky" in self.viewer._marker_regions
        assert bqplot_marks[0].visible
        assert bqplot_marks[0].colors == ["#00ff00"]
        assert bqplot_marks[0].opacities == [0.8]
        assert bqplot_marks[0].fill_opacities == [0.2]

        # Regions roundtrip
        out_regs_sky = self.viewer.get_markers(marker_name="my_sky")
        assert len(out_regs_sky.regions) == 1 and out_regs_sky.regions[0] is reg_sky
        out_regs_all = self.viewer.get_markers()
        assert (len(out_regs_all.regions) == 2 and out_regs_all.regions[0] is reg_pix
                and out_regs_all.regions[1] is reg_sky)

        # Make sure the other marker is not changed.
        bqplot_marks = self.viewer._get_marks(self.viewer._default_mark_tag_name)
        assert bqplot_marks[0].colors == ["red"]
        assert bqplot_marks[0].fill_opacities == [0]

        # Append to existing marker name.
        # API should not care if user mix stuff under the same name.
        reg_pix_2 = PolygonPixelRegion(PixCoord([0, 0, 1, 1], [0, 1, 1, 0]))
        reg_pix_3 = RectanglePixelRegion(PixCoord(3, 4), width=2, height=3)
        reg_pix_invalid = TextPixelRegion(PixCoord(3, 4), text="Invalid")
        self.viewer.marker = {"color": "blue", "alpha": 0.5, "fill": True}
        with pytest.warns(AstropyUserWarning, match="Failed to mark this region, skipping"):
            self.viewer.add_markers([reg_pix_2, reg_pix_3, reg_pix_invalid], marker_name="my_sky")
        out_regs_mixed = self.viewer.get_markers(marker_name="my_sky")
        assert (len(out_regs_sky.regions) == 3 and out_regs_mixed.regions[1] is reg_pix_2
                and out_regs_mixed.regions[2] is reg_pix_3)
        bqplot_marks = self.viewer._get_marks("my_sky")
        assert len(bqplot_marks) == 3
        assert bqplot_marks[0].visible
        assert bqplot_marks[0].colors == ["#00ff00"]
        assert bqplot_marks[0].opacities == [0.8]
        assert bqplot_marks[0].fill_opacities == [0.2]
        for mrk in bqplot_marks[1:]:
            assert mrk.visible
            assert mrk.colors == ["blue"]
            assert mrk.opacities == [0.5]
            assert mrk.fill_opacities == [0.2]

        # Just want to make sure nothing crashes. Zooming already testing elsewhere.
        # https://github.com/spacetelescope/jdaviz/pull/1971
        self.viewer.zoom_level = 'fit'

        # Remove markers with default name.
        self.viewer.remove_markers()
        assert list(self.viewer._marker_regions) == ["my_sky"]

        # Reset markers (runs remove_markers with marker_name set)
        self.viewer.reset_markers()
        assert len(self.viewer._marker_regions) == 0

        # Removing invalid marker is silent no-op.
        self.viewer.remove_markers(marker_name="does_not_exist")

        # NOTE: This changes the state of self.imviz for this test class!

        # Remaining data has no WCS but sky region given.
        self.imviz.app.data_collection.remove(self.imviz.app.data_collection[0])
        with pytest.warns(AstropyUserWarning, match="Failed to mark this region, skipping"):
            self.viewer.add_markers(reg_sky, marker_name="my_sky")

        self.imviz.app.data_collection.clear()
        with pytest.raises(ValueError, match="No reference data"):
            self.viewer.add_markers(reg_sky, marker_name="my_sky")


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
    calib_cat = CircleSkyRegion(SkyCoord(80.6609, -69.4524, unit='deg'), 0.1 * u.arcsec)
    imviz_helper.default_viewer.add_markers(calib_cat, marker_name='my_sky')
    bqplot_marks = imviz_helper.default_viewer._get_marks("my_sky")
    assert bqplot_marks[0].visible
    assert bqplot_marks[0].colors == ["red"]
    assert bqplot_marks[0].opacities == [1]
    assert bqplot_marks[0].fill_opacities == [0]
