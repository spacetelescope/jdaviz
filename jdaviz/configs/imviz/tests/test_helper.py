import numpy as np


def test_plugin_user_apis(imviz_helper):
    for plugin_name, plugin_api in imviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_create_new_viewer(imviz_helper, image_2d_wcs):
    # starts with one (default) viewer
    assert len(imviz_helper.app.get_viewer_ids()) == 1
    arr = np.ones((10, 10))

    data_label = 'image-data'
    viewer_name = 'user-created-viewer'
    imviz_helper.load_data(arr, data_label=data_label, show_in_viewer=False)
    imviz_helper.create_image_viewer(viewer_name=viewer_name)

    returned_data = imviz_helper.get_data(data_label)
    assert len(returned_data.shape) == 2

    # new image viewer created
    assert len(imviz_helper.app.get_viewer_ids()) == 2

    # there should be no data in the new viewer
    assert len(imviz_helper.app.get_viewer(viewer_name).data()) == 0

    # then add data, and check that data were added to the new viewer
    imviz_helper.app.add_data_to_viewer(viewer_name, data_label)
    assert len(imviz_helper.app.get_viewer(viewer_name).data()) == 1

    # remove data from the new viewer, check that it was removed
    imviz_helper.app.remove_data_from_viewer(viewer_name, data_label)
    assert len(imviz_helper.app.get_viewer(viewer_name).data()) == 0
