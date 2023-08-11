import numpy as np
import pytest

from astropy.nddata import NDData

from jdaviz.core.marks import FootprintOverlay
from jdaviz.configs.imviz.plugins.footprints.preset_regions import _all_apertures


def _get_markers_from_viewer(viewer):
    return [m for m in viewer.figure.marks if isinstance(m, FootprintOverlay)]


def test_user_api(imviz_helper, image_2d_wcs):
    arr = np.ones((10, 10))
    ndd = NDData(arr, wcs=image_2d_wcs)
    # load the image twice to test linking
    imviz_helper.load_data(ndd)
    imviz_helper.load_data(ndd)

    plugin = imviz_helper.plugins['Footprints']
    with plugin.as_active():
        assert plugin._obj.is_pixel_linked is True
        plugin._obj.vue_link_by_wcs()
        assert plugin._obj.is_pixel_linked is False

        # test that each of the supported instruments/presets work
        for preset in plugin.preset.choices:
            plugin.preset = preset

            viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
            assert len(viewer_marks) == len(_all_apertures.get(preset))

        # change the color/opacity of the first/default overlay
        default_color = plugin.color
        default_opacity = plugin.fill_opacity
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

        # test centering logic
        plugin.center_on_viewer()

    # with the plugin no longer active, marks should not be visible
    assert plugin._obj.is_active is False
    assert viewer_marks[0].visible is False
