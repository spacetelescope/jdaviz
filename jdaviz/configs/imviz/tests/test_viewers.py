def test_create_image_viewer(imviz_app):
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']
    imviz_app.create_image_viewer()
    assert imviz_app.app.get_viewer_ids() == ['imviz-0', 'imviz-1']
