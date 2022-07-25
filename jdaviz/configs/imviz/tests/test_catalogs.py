import pytest #not sure if I need this

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS

# testing that the plugin search does not crash when no data/image is provided
class TestCatalogs_NoImage():

    def test_plugin(self, imviz_helper):
        self.imviz = imviz_helper

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        assert not catalogs_plugin.results_available

# testing that every variable updates accordingly when the image/data provided does not have any results
class TestCatalogs_NoResults(BaseImviz_WCS_WCS):

    def test_plugin(self):
        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 0

# 2 more tests to-do: testing that every variable updates accordingly when the image/data provided does have results,
# testing that every variable updates accordingly when markers are cleared
