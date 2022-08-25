from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestLinksControl(BaseImviz_WCS_NoWCS):
    def test_plugin(self):
        lc_plugin = self.imviz.app.get_tray_item_from_name('imviz-links-control')

        lc_plugin.link_type = 'WCS'
        lc_plugin.wcs_use_affine = False
        lc_plugin.link_type = 'Pixels'

        # wcs_use_affine should revert/default to True
        assert lc_plugin.wcs_use_affine is True
