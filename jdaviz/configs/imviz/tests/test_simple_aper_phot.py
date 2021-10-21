from jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple import SimpleAperturePhotometry
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_plugin_wcs_dithered(self):
        self.imviz.link_data(link_type='wcs')  # They are dithered by 1 pixel on X
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle

        phot_plugin = SimpleAperturePhotometry(app=self.imviz.app)

        # Populate plugin menu items
        phot_plugin._on_viewer_data_changed()

        # UNTIL HERE
