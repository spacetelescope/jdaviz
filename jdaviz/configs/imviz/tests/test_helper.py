import numpy as np
import pytest


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(deconfigged_helper):
    for plugin_name, plugin_api in deconfigged_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_create_new_viewer(deconfigged_helper, image_2d_wcs):
    # starts with one (default) viewer
    assert len(deconfigged_helper._app.get_viewer_ids()) == 1
    arr = np.ones((10, 10))

    data_label = 'image-data'
    viewer_name = 'user-created-viewer'
    deconfigged_helper.load(arr, data_label=data_label, show_in_viewer=False)
    deconfigged_helper.create_image_viewer(viewer_name=viewer_name)

    # Test both the old and new API
    returned_data = deconfigged_helper.datasets[data_label].get_data()
    returned_data_old_api = deconfigged_helper.get_data(data_label)

    assert len(returned_data.shape) == 2
    assert len(returned_data_old_api.shape) == 2
    # Verify both APIs return equivalent data
    assert np.array_equal(returned_data, returned_data_old_api)

    # new image viewer created
    assert len(deconfigged_helper._app.get_viewer_ids()) == 2

    # there should be no data in the new viewer
    assert len(deconfigged_helper._app.get_viewer(viewer_name).data()) == 0

    # then add data, and check that data were added to the new viewer
    deconfigged_helper._app.add_data_to_viewer(viewer_name, data_label)
    assert len(deconfigged_helper._app.get_viewer(viewer_name).data()) == 1

    # remove data from the new viewer, check that it was removed
    deconfigged_helper._app.remove_data_from_viewer(viewer_name, data_label)
    assert len(deconfigged_helper._app.get_viewer(viewer_name).data()) == 0


def test_temporary_imviz_current_app(deconfigged_helper):
    from jdaviz.configs.imviz.helper import _current_app
    assert _current_app == deconfigged_helper
