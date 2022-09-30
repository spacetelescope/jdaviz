from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestLinksControl(BaseImviz_WCS_WCS):
    def test_plugin(self):
        lc_plugin = self.imviz.app.get_tray_item_from_name('imviz-links-control')

        lc_plugin.link_type.selected = 'WCS'
        lc_plugin.wcs_use_affine = False
        lc_plugin.link_type.selected = 'Pixels'

        # wcs_use_affine should revert/default to True
        assert lc_plugin.wcs_use_affine is True
