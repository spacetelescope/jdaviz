import pytest

from astropy.table import Table
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestLinksControl(BaseImviz_WCS_WCS):
    def test_plugin(self):
        lc_plugin = self.imviz.app.get_tray_item_from_name('imviz-links-control')

        lc_plugin.link_type.selected = 'WCS'
        lc_plugin.wcs_use_affine = False
        lc_plugin.link_type.selected = 'Pixels'

        # wcs_use_affine should revert/default to True
        assert lc_plugin.wcs_use_affine is True

        # adding markers should disable changing linking from both UI and API
        assert lc_plugin.need_clear_markers is False
        tbl = Table({'x': (0, 0), 'y': (0, 1)})
        self.viewer.add_markers(tbl, marker_name='xy_markers')

        assert lc_plugin.need_clear_markers is True
        with pytest.raises(ValueError, match="cannot change linking"):
            lc_plugin.link_type.selected = 'WCS'
        assert lc_plugin.link_type.selected == 'Pixels'

        lc_plugin.vue_reset_markers()

        assert lc_plugin.need_clear_markers is False
        lc_plugin.link_type.selected = 'WCS'
