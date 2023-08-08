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
    imviz_helper.load_data(ndd)

    plugin = imviz_helper.plugins['Footprints']
    with plugin.as_active():
        # test that each of the supported instruments work
        for instrument in plugin.instrument.choices:
            plugin.instrument = instrument

            viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
            assert len(viewer_marks) == len(_all_apertures.get(instrument))

        # change the color/opacity of the first/default footprint
        default_color = plugin.color
        default_opacity = plugin.fill_opacity
        plugin.color = '#ffffff'
        plugin.fill_opacity = 0.5

        viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
        assert viewer_marks[0].colors == ['#ffffff']
        assert viewer_marks[0].fill_opacities == [0.5]

        # add a second footprint from the API
        with pytest.raises(ValueError):
            plugin.add_footprint(plugin.footprint.selected)

        plugin.add_footprint('second footprint')
        assert plugin.footprint.selected == 'second footprint'

        # color should reset, opacity should carry over
        assert plugin.color == default_color
        assert plugin.fill_opacity != default_opacity

        plugin.color = '#000000'

        # rename footprint
        plugin.rename_footprint('second footprint', 'renamed footprint')
        assert plugin.footprint.selected == 'renamed footprint'
        assert plugin.color == '#000000'

        # remove footprint, selection should default to first entry and traitlets update
        plugin.remove_footprint('renamed footprint')
        assert plugin.footprint.selected == 'default'
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

    # with the plugin no longer active, marks should not be visible
    assert plugin._obj.is_active is False
    assert viewer_marks[0].visible is False
