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
    _prev_limits = None

    def __init__(self, *args, **kwargs):
        # NOTE: anything here most likely won't be called by viewers because of inheritance order
        super().__init__(*args, **kwargs)

    def _subscribe_to_layers_update(self):
        # subscribe to new layers
        self._expected_subset_layers = []
        self.state.add_callback('layers', self._on_layers_update)

    def _get_layer(self, label):
        for layer in self.state.layers:
            if layer.layer.label == label:
                return layer

    def _expected_subset_layer_default(self, layer):
        # default visibility based on the visibility of the "parent" data layer
        layer.visible = self._get_layer(layer.layer.data.label).visible

    def _on_layers_update(self, layers=None):
        if self.__class__.__name__ == 'MosvizTableViewer':
            # MosvizTableViewer uses this as a mixin, but we do not need any of this layer
            # logic there
            return

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

        if not len(self._expected_subset_layers):
            return
        # we'll make a deepcopy so that we can remove entries from the self._expected_subset_layers
        # to avoid recursion, but also handle multiple layers for the same subset
        expected_subset_layers = self._expected_subset_layers[:]
        for layer in self.state.layers:
            if layer.layer.label in expected_subset_layers:
                if layer.layer.label in self._expected_subset_layers:
                    self._expected_subset_layers.remove(layer.layer.label)
                self._expected_subset_layer_default(layer)

    def _on_subset_create(self, msg):
        if self.__class__.__name__ == 'MosvizTableViewer':
            # MosvizTableViewer uses this as a mixin, but we do not need any of this layer
            # logic there
            return
        # NOTE: the subscription to this method is handled in ConfigHelper
        # we don't have access to the actual subset yet to tell if its spectral or spatial, so
        # we'll store the name of this new subset and change the default linewidth when the
        # layers are added
        self._expected_subset_layers.append(msg.subset.label)

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

    @property
    def reference_id(self):
        return self._reference_id
