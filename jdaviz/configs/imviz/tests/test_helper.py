

def test_plugin_user_apis(imviz_helper):
    for plugin_name, plugin_api in imviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
