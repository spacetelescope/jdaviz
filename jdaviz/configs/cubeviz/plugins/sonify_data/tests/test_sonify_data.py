
def test_sonify_data(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger, data_label="test")
    sonify_plg = cubeviz_helper.app.get_tray_item_from_name('cubeviz-sonify-data')
    assert sonify_plg.stream_active
