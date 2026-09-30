# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest


@pytest.mark.parametrize('helper_name', [
    'imviz_helper', 'cubeviz_helper', 'mosviz_helper', 'rampviz_helper',
])
def test_image_aspect_survives_hidden_view_and_resumes_after_reveal(request, helper_name):
    helper = request.getfixturevalue(helper_name)
    app = helper._app
    viewer = app.get_viewer_by_id(f'{app.config}-0')
    viewer.state.aspect = 'equal'
    viewer.shape = (200, 400)
    viewer._sync_figure_aspect()
    assert viewer.state._axes_aspect_ratio == 0.5

    # Both fully hidden widgets and collapsed single dimensions can occur
    # while the browser is applying layout or notebook visibility changes.
    for hidden_shape in ((0, 0), (0, 400), (300, 0)):
        viewer.shape = hidden_shape
        viewer._sync_figure_aspect()
        assert viewer.state._axes_aspect_ratio == 0.5

    viewer.shape = (300, 400)
    viewer._sync_figure_aspect()
    assert viewer.state._axes_aspect_ratio == 0.75

    # A genuinely missing view retains the upstream reset behavior.
    viewer.shape = None
    viewer._sync_figure_aspect()
    assert viewer.state._axes_aspect_ratio is None
