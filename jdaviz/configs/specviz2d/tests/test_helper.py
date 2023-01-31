from jdaviz import Specviz


def test_helper(specviz2d_helper, spectrum1d):
    specviz2d_helper.load_data(spectrum_1d=spectrum1d)
    assert isinstance(specviz2d_helper.specviz, Specviz)

    specviz2d_helper.app.data_collection[0].meta['Trace'] = "Test"

    returned_data = specviz2d_helper.get_data()
    assert len(returned_data.shape) == 1


def test_plugin_user_apis(specviz2d_helper):
    for plugin_name, plugin_api in specviz2d_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
