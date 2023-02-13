from specutils import Spectrum1D
from jdaviz import Specviz


def test_helper(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d)
    assert isinstance(specviz2d_helper.specviz, Specviz)

    specviz2d_helper.app.data_collection[0].meta['Trace'] = "Test"

    returned_data = specviz2d_helper.get_data("Spectrum 2D")
    assert len(returned_data.shape) == 1
    assert isinstance(returned_data, Spectrum1D)


def test_plugin_user_apis(specviz2d_helper):
    for plugin_name, plugin_api in specviz2d_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
