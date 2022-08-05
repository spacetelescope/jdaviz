def test_nested_helper(cubeviz_helper):
    '''Ensures the Cubeviz helper is always returned, even after the Specviz helper is called'''
    # Force Specviz helper to instantiate
    cubeviz_helper.specviz

    assert cubeviz_helper.app._jdaviz_helper == cubeviz_helper

    # The viewers also have a callthrough to the app's _jdaviz_helper attribute
    spec_viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')
    assert spec_viewer.jdaviz_helper == cubeviz_helper
