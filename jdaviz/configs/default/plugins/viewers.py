import numpy as np

from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer

from jdaviz.components.toolbar_nested import NestedJupyterToolbar
from jdaviz.core.registries import viewer_registry


__all__ = ['JdavizViewerMixin']

viewer_registry.add("g-profile-viewer", label="Profile 1D", cls=BqplotProfileView)
viewer_registry.add("g-image-viewer", label="Image 2D", cls=BqplotImageView)
viewer_registry.add("g-table-viewer", label="Table", cls=TableViewer)


class JdavizViewerMixin:
    toolbar_nested = None
    tools_nested = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # subscribe to new layers
        self.state.add_callback('layers', self._on_layers_update)

    def _on_layers_update(self, layers=None):
        selected_data_items = self.jdaviz_app._viewer_item_by_id(self.reference_id)['selected_data_items']  # noqa

        for data_id, visibility in selected_data_items.items():
            label = next((x['name'] for x in self.jdaviz_app.state.data_items
                          if x['id'] == data_id), None)

            visibilities = []
            for layer in self.state.layers:
                if layer.layer.data.label == label:
                    visibilities.append(layer.visible)
            if np.all(visibilities):
                selected_data_items[data_id] = 'visible'
            elif np.any(visibilities):
                selected_data_items[data_id] = 'mixed'
            else:
                selected_data_items[data_id] = 'hidden'

    def _initialize_toolbar_nested(self, default_tool_priority=[]):
        # would be nice to call this from __init__,
        # but because of inheritance order that isn't simple
        self.toolbar_nested = NestedJupyterToolbar(self, self.tools_nested, default_tool_priority)

    @property
    def jdaviz_app(self):
        """The Jdaviz application tied to the viewer."""
        return self.session.jdaviz_app

    @property
    def jdaviz_helper(self):
        """The Jdaviz configuration helper tied to the viewer."""
        return self.jdaviz_app._jdaviz_helper

#    @property
#    def viewer_id(self):
#        for vid, viewer in self.jdaviz_app._viewer_store.items():
#            if viewer == self:
#                return vid

    @property
    def reference_id(self):
        return self._reference_id
