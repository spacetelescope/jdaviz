
def test_plugin_open(cubeviz_helper):
    assert cubeviz_helper.app.state.drawer is False

    plugin_names = [ti['name'] for ti in cubeviz_helper.app.state.tray_items]
    plugin_index = plugin_names.index('g-plot-options')

    # test opening from API
    sv = cubeviz_helper.app.get_viewer('spectrum-viewer')
    plugin = cubeviz_helper.app.get_tray_item_from_name('g-plot-options')
    sv.open_plot_options()
    assert cubeviz_helper.app.state.drawer is True
    assert cubeviz_helper.app.state.tray_items_open == [plugin_index]
    assert plugin.selected_viewer == 'spectrum-viewer'
