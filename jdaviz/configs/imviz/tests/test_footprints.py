import numpy as np
import pytest
import astropy.units as u
from astropy.nddata import NDData
from astropy.coordinates import SkyCoord
from regions import PixCoord, CirclePixelRegion, CircleSkyRegion, RectangleSkyRegion

from jdaviz.core.marks import FootprintOverlay
from jdaviz.configs.imviz.plugins.footprints.preset_regions import _all_apertures
from astropy.wcs import WCS

pytest.importorskip("pysiaf")


def _get_markers_from_viewer(viewer):
    if hasattr(viewer, '_obj'):
        viewer = viewer._obj
    return [m for m in viewer.figure.marks if isinstance(m, FootprintOverlay)]


def test_user_api(imviz_helper, image_2d_wcs, tmp_path):
    arr = np.ones((10, 10))
    ndd = NDData(arr, wcs=image_2d_wcs)
    # load the image twice to test linking
    imviz_helper.load_data(ndd)
    imviz_helper.load_data(ndd)

    plugin = imviz_helper.plugins['Footprints']
    default_color = plugin.color
    default_opacity = plugin.fill_opacity
    plugin.color = '#333333'
    with plugin.as_active():
        assert plugin._obj.is_pixel_linked is True
        plugin._obj.vue_link_by_wcs()
        assert plugin._obj.is_pixel_linked is False

        # test that each of the supported instruments/presets work
        for preset in (preset for preset in plugin.preset.choices if preset != 'From File...'):
            plugin.preset = preset

            viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
            assert len(viewer_marks) == len(_all_apertures.get(preset))

        # regression test for user-set traitlets (specifically color) being reset
        # when the plugin is opened
        assert plugin.color == '#333333'
        assert viewer_marks[0].colors == ['#333333']

        # change the color/opacity of the first/default overlay
        plugin.color = '#ffffff'
        plugin.fill_opacity = 0.5

        viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
        assert viewer_marks[0].visible is True
        assert viewer_marks[0].colors == ['#ffffff']
        assert viewer_marks[0].fill_opacities == [0.5]

        # add a second overlay from the API
        with pytest.raises(ValueError):
            plugin.add_overlay(plugin.overlay.selected)

        plugin.add_overlay('second overlay')
        assert plugin.overlay.selected == 'second overlay'

        # color should reset, opacity should carry over
        assert plugin.color == default_color
        assert plugin.fill_opacity != default_opacity

        plugin.color = '#000000'

        # rename overlay
        plugin.rename_overlay('second overlay', 'renamed overlay')
        assert plugin.overlay.selected == 'renamed overlay'
        assert plugin.color == '#000000'

        # remove overlay, selection should default to first entry and traitlets update
        plugin.remove_overlay('renamed overlay')
        assert plugin.overlay.selected == 'default'
        assert plugin.color == '#ffffff'

        # test toggling visibility of markers
        viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
        assert viewer_marks[0].visible is True
        plugin.visible = False
        assert viewer_marks[0].visible is False
        plugin.visible = True
        assert viewer_marks[0].visible is True
        plugin.viewer.selected = []
        assert viewer_marks[0].visible is False
        plugin.viewer.select_all()
        assert viewer_marks[0].visible is True

        # test centering logic (for now just that it doesn't fail)
        plugin.center_on_viewer()

        # test from file/API ability
        reg = plugin.overlay_regions
        plugin.import_region(reg)
        assert plugin.preset.selected == 'From File...'
        viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
        assert len(viewer_marks) == len(reg)
        # test that importing a different region updates the marks and also that
        # a single region is supported
        plugin.import_region(reg[0])
        viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
        assert len(viewer_marks) == 1
        # clearing the file should default to the PREVIOUS preset (last from the for-loop above)
        plugin._obj.vue_file_import_cancel()
        assert plugin.preset.selected == preset

        tmp_file = str(tmp_path / 'test_region.reg')
        reg.write(tmp_file, format='ds9')
        plugin.import_region(tmp_file)
        assert plugin.preset.selected == 'From File...'
        assert plugin.preset.from_file == tmp_file

        # test single region (footprints contain multiple regions)
        valid_region_sky = CircleSkyRegion(center=SkyCoord(42, 43, unit='deg', frame='fk5'),
                                           radius=3 * u.deg)
        plugin.import_region(valid_region_sky)

        # test RectangleSkyRegion -> RectanglePixelRegion
        valid_region_sky = RectangleSkyRegion(center=SkyCoord(42, 43, unit='deg', frame='fk5'),
                                              height=3 * u.deg, width=2 * u.deg)
        plugin.import_region(valid_region_sky)

        tmp_invalid_path = str(tmp_path / 'invalid_path.reg')
        with pytest.raises(ValueError):
            plugin.import_region(tmp_invalid_path)
        with pytest.raises(TypeError):
            plugin.import_region(5)

        invalid_region = CirclePixelRegion(PixCoord(x=8, y=7), radius=3.5)
        with pytest.raises(ValueError):
            plugin.import_region(invalid_region)
        tmp_invalid_file = str(tmp_path / 'test_invalid_region.reg')
        invalid_region.write(tmp_invalid_file, format='ds9')
        with pytest.raises(ValueError):
            plugin.import_region(tmp_invalid_file)
        assert plugin.preset.selected == preset

    # with the plugin no longer active, marks should not be visible
    assert plugin._obj.is_active is False
    viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
    assert viewer_marks[0].visible is False


def test_api_after_linking(imviz_helper):
    # custom image to enable visual test in a notebook
    arr = np.ones((300, 300))
    image_2d_wcs = WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
                        'CRPIX1': 1, 'CRVAL1': 337.5202808,
                        'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
                        'CRPIX2': 1, 'CRVAL2': -20.833333059999998})

    viewer = imviz_helper.app.get_viewer_by_id('imviz-0')

    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd)
    imviz_helper.load_data(ndd)

    plugin = imviz_helper.plugins['Footprints']
    with plugin.as_active():

        pointing = {'name': ['pt'], 'ra': [337.51], 'dec': [-20.77], 'pa': [0]}
        plugin.color = 'green'
        plugin.add_overlay(pointing['name'][0])
        plugin.ra = pointing['ra'][0]
        plugin.dec = pointing['dec'][0]
        plugin.pa = pointing['pa'][0]

        # when pixel linked are any marks displayed
        viewer_marks = _get_markers_from_viewer(viewer)
        no_marks_displayed = all(not mark.visible for mark in viewer_marks)
        assert no_marks_displayed is True

        # link by wcs and retest
        imviz_helper.link_data(link_type='wcs')

        viewer_marks = _get_markers_from_viewer(viewer)
        # distinguish default from custom overlay with color
        marks_displayed = any(mark.visible and mark.colors[0] == 'green'
                              for mark in viewer_marks)

        # when wcs linked are any marks displayed
        assert marks_displayed is True


def test_footprint_updates_on_rotation(imviz_helper):
    image_2d_wcs = WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg',
                        'CRPIX1': 1, 'CRVAL1': 337.5202808,
                        'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg',
                        'CRPIX2': 1, 'CRVAL2': -20.833333059999998,
                        'CD1_1': 0.0005, 'CD1_2': 0.005,
                        'CD2_1': -0.005, 'CD2_2': -0.0005})

    arr = np.random.normal(size=(10, 10))
    ndd = NDData(arr, wcs=image_2d_wcs)

    imviz_helper.load_data(ndd)
    imviz_helper.link_data(link_type='wcs')

    footprints = imviz_helper.plugins['Footprints']
    footprints.keep_active = True

    # this is near the pixel origin:
    rectangle_center = SkyCoord(337.5202808, -20.83333306, unit='deg')

    # this is the opposite corner of the image:
    opposite_corner = SkyCoord(337.5791498, -20.88832297, unit='deg')

    # Put a MIRI footprint at the far corner:
    footprints.preset = 'MIRI'
    footprints.ra = opposite_corner.ra.deg
    footprints.dec = opposite_corner.dec.deg
    miri_region = footprints.overlay_regions[0]

    # create a second footprint for a rectangular sky region near the pixel origin:
    footprints.add_overlay('2')

    rectangle_region = RectangleSkyRegion(
        center=rectangle_center,
        height=1 * u.arcmin,
        width=2 * u.arcmin,
        angle=45 * u.deg
    )

    footprints.import_region(rectangle_region)

    # ensure that the footprints are where we expect them:
    assert rectangle_region.contains(rectangle_center, image_2d_wcs)
    assert not rectangle_region.contains(opposite_corner, image_2d_wcs)

    assert not miri_region.contains(rectangle_center, image_2d_wcs)
    assert miri_region.contains(opposite_corner, image_2d_wcs)

    marks = _get_markers_from_viewer(imviz_helper.default_viewer)

    # check that the rectangle region appears near the bottom of the viewer:
    assert np.concatenate([marks[0].y, marks[1].y]).min() < -3

    # now rotate to north-up east-left:
    orientation = imviz_helper.plugins['Orientation']._obj
    orientation.create_north_up_east_left(set_on_create=True)

    # If all footprint orientations have been updated, the lowest
    # mark should still be centered low. If the footprint
    # orientations aren't updated, both footprints will be
    # at the top of the viewer, and this test will fail.
    marks = _get_markers_from_viewer(imviz_helper.default_viewer)
    assert np.concatenate([marks[0].y, marks[1].y]).min() < -3
