import numpy as np
import pytest
import astropy.units as u
from astropy.nddata import NDData
from astropy.coordinates import SkyCoord
from regions import PixCoord, CirclePixelRegion, CircleSkyRegion, RectangleSkyRegion

from jdaviz.core.marks import FootprintOverlay
from jdaviz.configs.imviz.plugins.footprints.preset_regions import _all_apertures

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
