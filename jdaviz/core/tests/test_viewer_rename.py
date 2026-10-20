# Licensed under a 3-clause BSD style license - see LICENSE.rst

import pytest
from traitlets import Any

from jdaviz.core.template_mixin import LayerSelect


@pytest.mark.parametrize('update_id', [False, True])
@pytest.mark.parametrize('selected', ['added', ['imviz-0', 'added'], ['imviz-0']])
def test_layer_select_preserves_selection_on_viewer_rename(imviz_helper, update_id, selected):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    viewer = app.get_viewer_by_id('added')
    plugin = app.get_tray_item_from_name('g-plot-options')
    # Use an independent viewer trait so ViewerSelect's own rename handling
    # cannot update the selection before LayerSelect receives the message.
    plugin.add_traits(rename_test_viewers=Any(selected))
    selector = LayerSelect(plugin, 'layer_items', 'layer_selected', 'rename_test_viewers')

    app._update_viewer_reference_name('added', 'renamed', update_id=update_id)

    expected = (['renamed' if reference == 'added' else reference for reference in selected]
                if isinstance(selected, list) else 'renamed')
    assert selector.viewer == expected
    assert plugin.rename_test_viewers == expected
    assert selector.viewer_objs == ([app.get_viewer(reference) for reference in expected]
                                    if isinstance(expected, list) else [viewer])
    assert app.get_viewer_by_id('renamed' if update_id else 'added') is viewer
