import pytest


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_data_selection(cubeviz_helper, spectrum1d_cube, tmpdir):
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
    app.set_data_visibility('cubeviz-0', app.state.data_items[1]['name'],
                            visible=True, replace=True)

    assert len(fv.layers) == 2
    assert len([layer for layer in fv.layers if layer.visible]) == 1

    # but also has the option to display multiple layers
    app.set_data_visibility('cubeviz-0', app.state.data_items[0]['name'],
                            visible=True, replace=False)

    assert len(fv.layers) == 2
    assert len([layer for layer in fv.layers if layer.visible]) == 2

    app.vue_data_item_remove({'item_name': app.state.data_items[1]['name']})

    assert len(fv.layers) == 1
