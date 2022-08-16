import numpy as np

from glue.core.subset import RoiSubsetState
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

    @property
    def native_marks(self):
        """
        Return all marks that are Lines/LinesGL objects (and not subclasses)
        """
        return [m for m in self.figure.marks if m.__class__.__name__ in ['Lines', 'LinesGL']]

    @property
    def custom_marks(self):
        """
        Return all marks that are not Lines/LinesGL objects (but can be subclasses)
        """
        return [m for m in self.figure.marks if m.__class__.__name__ not in ['Lines', 'LinesGL']]

    def _subscribe_to_layers_update(self):
        # subscribe to new layers
        self._expected_subset_layers = []
        self.state.add_callback('layers', self._on_layers_update)

    def _get_layer(self, label):
        for layer in self.state.layers:
            if layer.layer.label == label:
                return layer

    def _expected_subset_layer_default(self, layer_state):
        if self.__class__.__name__ == 'CubevizImageView':
            # Do not override default for subsets as for some reason
            # this isn't getting called when they're first added, but rather when
            # the next state change is made (for example: manually changing the visibility)
            return

        # default visibility based on the visibility of the "parent" data layer
        layer_state.visible = self._get_layer(layer_state.layer.data.label).visible

    def _update_layer_icons(self):
        # update visible_layers (TODO: move this somewhere that can update on color change, etc)
        def _get_layer_color(layer):
            if getattr(self.state, 'color_mode', None) == 'Colormaps':
                for subset in self.jdaviz_app.data_collection.subset_groups:
                    if subset.label == layer.layer.label:
                        # then we still want to show the color for a subset
                        return layer.color
                # then this is a data-layer in colormap mode, so we'll ignore the color
                return ''
            return layer.color

        def _get_layer_info(layer):
            if self.__class__.__name__ == 'CubevizProfileView' and len(layer.layer.data.shape) == 3:
                suffix = f" (collapsed: {self.state.function})"
            else:
                suffix = ""

            # then the underlying data is cube-like and we're in the profile viewer, so we
            # want to include the collapse function *unless* the layer is a spectral subset
            for subset in self.jdaviz_app.data_collection.subset_groups:
                if subset.label == layer.layer.label:
                    if isinstance(subset.subset_state, RoiSubsetState):
                        return "mdi-chart-scatter-plot", suffix
                    else:
                        return "mdi-chart-bell-curve", ""
            return "", suffix

            return '', ''

        visible_layers = {}
        for layer in self.state.layers[::-1]:
            if layer.visible:
                prefix_icon, suffix = _get_layer_info(layer)
                visible_layers[layer.layer.label] = {'color': _get_layer_color(layer),
                                                     'prefix_icon': prefix_icon,
                                                     'suffix_label': suffix}

        viewer_item = self.jdaviz_app._viewer_item_by_id(self.reference_id)
        viewer_item['visible_layers'] = visible_layers

    def _on_layers_update(self, layers=None):
        if self.__class__.__name__ == 'MosvizTableViewer':
            # MosvizTableViewer uses this as a mixin, but we do not need any of this layer
            # logic there
            return

        viewer_item = self.jdaviz_app._viewer_item_by_id(self.reference_id)
        selected_data_items = viewer_item['selected_data_items']

        # update selected_data_items
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

        self._update_layer_icons()

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
        if msg.subset.label not in self._expected_subset_layers and msg.subset.label:
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
