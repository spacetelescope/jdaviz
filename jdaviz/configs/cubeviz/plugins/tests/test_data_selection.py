import pytest


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_moment_calculation(cubeviz_helper, spectrum1d_cube, tmpdir):
    app = cubeviz_helper.app
    # NOTE: these are the same underlying data.  This works fine for the current scope
    # of the tests (to make sure checking/unchecking operations change the data exposed
    # in the viewer), but will need to be more advanced if we extend tests here to
    # cover scrubbing/linking/etc
    app.add_data(spectrum1d_cube, 'cube1')
    app.add_data(spectrum1d_cube, 'cube2')
    app.add_data_to_viewer('flux-viewer', 'cube1')
    fv = app.get_viewer('flux-viewer')

    assert len(app.state.data_items) == 2
    assert len(fv.data()) == 1
    assert fv.data()[0].label == app.state.data_items[0]['name']

    # by default, the image viewers will use replace logic
    app.vue_data_item_selected({'id': 'cubeviz-0',
                                'item_id': app.state.data_items[1]['id'],
                                'checked': True,
                                'replace': True})

    assert len(fv.data()) == 1
    assert fv.data()[0].label == app.state.data_items[1]['name']

    # but also has the option to display multiple layers
    app.vue_data_item_selected({'id': 'cubeviz-0',
                                'item_id': app.state.data_items[0]['id'],
                                'checked': True,
                                'replace': False})

    assert len(fv.data()) == 2

    app.vue_data_item_remove({'item_name': app.state.data_items[1]['name']})

    assert len(fv.data()) == 1
