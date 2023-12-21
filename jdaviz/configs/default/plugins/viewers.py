import numpy as np
from echo import delay_callback

from glue.viewers.scatter.state import ScatterLayerState as BqplotScatterLayerState
from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.components.toolbar_nested import NestedJupyterToolbar
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.registries import viewer_registry
from jdaviz.core.user_api import ViewerUserApi
from jdaviz.utils import ColorCycler, get_subset_type

__all__ = ['JdavizViewerMixin']

viewer_registry.add("g-profile-viewer", label="Profile 1D", cls=BqplotProfileView)
viewer_registry.add("g-image-viewer", label="Image 2D", cls=BqplotImageView)
viewer_registry.add("g-table-viewer", label="Table", cls=TableViewer)


class JdavizViewerMixin:
    toolbar = None
    tools_nested = []
    _prev_limits = None
    _native_mark_classnames = ('Lines', 'LinesGL', 'FRBImage', 'Contour')

    def __init__(self, *args, **kwargs):
        # NOTE: anything here most likely won't be called by viewers because of inheritance order
        super().__init__(*args, **kwargs)

        # Allow each viewer to cycle through colors for each new addition to the viewer:
        self.color_cycler = ColorCycler()

    @property
    def user_api(self):
        # default exposed user APIs.  Can override this method in any particular viewer.
        if isinstance(self, BqplotImageView):
            if isinstance(self, AstrowidgetsImageViewerMixin):
                expose = ['save',
                          'center_on', 'offset_by', 'zoom_level', 'zoom',
                          'colormap_options', 'set_colormap',
                          'stretch_options', 'stretch',
                          'autocut_options', 'cuts',
                          'marker', 'add_markers', 'remove_markers', 'reset_markers',
                          'blink_once', 'reset_limits']
            else:
                # cubeviz image viewers don't inherit from AstrowidgetsImageViewerMixin yet,
                # but also shouldn't expose set_limits because of equal aspect ratio concerns
                expose = []
        elif isinstance(self, TableViewer):
            expose = []
        else:
            expose = ['set_limits', 'reset_limits']
        return ViewerUserApi(self, expose=expose)

    def reset_limits(self):
        """
        Reset viewer axes limits.
        """
        self.state.reset_limits()

    def set_limits(self, x_min=None, x_max=None, y_min=None, y_max=None):
        """
        Set viewer axes limits.

        Parameters
        ----------
        x_min : float or None, optional
            lower-limit of x-axis (in current axes units)
        x_max: float or None, optional
            upper-limit of x-axis (in current axes units)
        y_min : float or None, optional
            lower-limit of y-axis (in current axes units)
        y_max: float or None, optional
            upper-limit of y-axis (in current axes units)
        """
        for val in (x_min, x_max, y_min, y_max):
            if val is not None and not isinstance(val, (float, int)):
                raise TypeError('all arguments must be None, int, or float')

        with delay_callback(self.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            if x_min is not None:
                self.state.x_min = x_min
            if x_max is not None:
                self.state.x_max = x_max
            if y_min is not None:
                self.state.y_min = y_min
            if y_max is not None:
                self.state.y_max = y_max

    @property
    def native_marks(self):
        """
        Return all marks that are Lines/LinesGL objects (and not subclasses)
        """
        return [m for m in self.figure.marks
                if m.__class__.__name__ in self._native_mark_classnames]

    @property
    def custom_marks(self):
        """
        Return all marks that are not Lines/LinesGL objects (but can be subclasses)
        """
        return [m for m in self.figure.marks
                if m.__class__.__name__ not in self._native_mark_classnames]

    def _subscribe_to_layers_update(self):
        # subscribe to new layers
        self._expected_subset_layers = []
        self._layers_with_defaults_applied = []
        self.state.add_callback('layers', self._on_layers_update)

    def _get_layer(self, label):
        for layer in self.state.layers:
            if layer.layer.label == label:
                return layer

    def _apply_layer_defaults(self, layer_state):
        if hasattr(layer_state, 'as_steps'):
            if layer_state.layer.label != layer_state.layer.data.label:
                # then this is a subset, so default based on the parent data layer
                layer_state.as_steps = self._get_layer(layer_state.layer.data.label).as_steps
            else:
                # default to not plotting with as_steps (despite glue defaulting to True)
                layer_state.as_steps = False
            # whenever as_steps changes, we need to redraw the uncertainties (if enabled)
            layer_state.add_callback('as_steps', self._show_uncertainty_changed)

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
            if isinstance(layer, BqplotScatterLayerState):
                # then this could be a scatter layer in an image viewer,
                # so we'll ignore the color_mode
                return layer.color
            if getattr(self.state, 'color_mode', None) == 'Colormaps':
                for subset in self.jdaviz_app.data_collection.subset_groups:
                    if subset.label == layer.layer.label:
                        # then we still want to show the color for a subset
                        return layer.color
                # then this is a data-layer in colormap mode, so we'll ignore the color
                return ''
            return layer.color

        def _get_layer_linewidth(layer):
            linewidth = getattr(layer, 'linewidth', 0)
            return min(linewidth, 6)

        def _get_layer_info(layer):
            if self.__class__.__name__ == 'CubevizProfileView' and len(layer.layer.data.shape) == 3:
                suffix = f" (collapsed: {self.state.function})"
            else:
                suffix = ""

            if 'Trace' in layer.layer.data.meta:
                return "mdi-chart-line-stacked", ""

            # then the underlying data is cube-like and we're in the profile viewer, so we
            # want to include the collapse function *unless* the layer is a spectral subset
            for subset in self.jdaviz_app.data_collection.subset_groups:
                if subset.label == layer.layer.label:
                    subset_type = get_subset_type(subset)
                    if subset_type == 'spatial':
                        return "mdi-chart-scatter-plot", suffix
                    else:
                        return "mdi-chart-bell-curve", ""
            return "", suffix

        visible_layers = {}
        for layer in self.state.layers[::-1]:
            if layer.visible:
                prefix_icon, suffix = _get_layer_info(layer)
                visible_layers[layer.layer.label] = {'color': _get_layer_color(layer),
                                                     'linewidth': _get_layer_linewidth(layer),
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
        if viewer_item is None:
            return
        selected_data_items = viewer_item.get('selected_data_items', {})

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

        # we'll make a deepcopy so that we can remove entries from the self._expected_subset_layers
        # to avoid recursion, but also handle multiple layers for the same subset
        expected_subset_layers = self._expected_subset_layers[:]
        for layer in self.state.layers:
            layer_info = {'data_label': layer.layer.data.label,
                          'layer_label': layer.layer.label}
            if layer_info not in self._layers_with_defaults_applied:
                self._layers_with_defaults_applied.append(layer_info)
                self._apply_layer_defaults(layer)

            if layer.layer.label in expected_subset_layers:
                if layer.layer.label in self._expected_subset_layers:
                    self._expected_subset_layers.remove(layer.layer.label)
                self._expected_subset_layer_default(layer)

    def _on_subset_create(self, msg):
        from jdaviz.configs.mosviz.plugins.viewers import MosvizTableViewer
        if isinstance(self, MosvizTableViewer):
            # MosvizTableViewer uses this as a mixin, but we do not need any of this layer
            # logic there
            return

        # NOTE: the subscription to this method is handled in ConfigHelper
        # we don't have access to the actual subset yet to tell if its spectral or spatial, so
        # we'll store the name of this new subset and change the default linewidth when the
        # layers are added
        if msg.subset.label not in self._expected_subset_layers and msg.subset.label:
            self._expected_subset_layers.append(msg.subset.label)

    def _on_subset_delete(self, msg):
        """
        This is needed to remove the "ghost" subset left over when the subset tool is active,
        and the active subset is deleted. https://github.com/spacetelescope/jdaviz/issues/2499
        is open to revert/update this if it ends up being addressed upstream in
        https://github.com/glue-viz/glue-jupyter/issues/401.
        """
        from jdaviz.configs.mosviz.plugins.viewers import MosvizTableViewer
        if isinstance(self, MosvizTableViewer):
            # MosvizTableViewer uses this as a mixin, but we do not need any of this layer
            # logic there
            return

        subset_tools = ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                        'bqplot:circannulus', 'bqplot:xrange']

        if not len(self.session.edit_subset_mode.edit_subset):
            if self.toolbar.active_tool_id in subset_tools:
                if (hasattr(self.toolbar, "default_tool_priority") and
                        len(self.toolbar.default_tool_priority)):
                    self.toolbar.active_tool_id = self.toolbar.default_tool_priority[0]
                else:
                    self.toolbar.active_tool = None

    @property
    def active_image_layer(self):
        """Active image layer in the viewer, if available."""
        # Find visible layers
        visible_layers = [layer for layer in self.state.layers
                          if (layer.visible and layer_is_image_data(layer.layer))]

        if len(visible_layers) == 0:
            return None

        return visible_layers[-1]

    def initialize_toolbar(self, default_tool_priority=[]):
        # NOTE: this overrides glue_jupyter.IPyWidgetView
        self.toolbar = NestedJupyterToolbar(self, self.tools_nested, default_tool_priority)

    @property
    def tools(self):
        # NOTE: this overrides the default list of tools for the BasicJupyterToolbar by
        # returning a flattened version of self.tools_nested
        return list(self.toolbar.tools.keys())

    @property
    def jdaviz_app(self):
        """The Jdaviz application tied to the viewer."""
        return self.session.jdaviz_app

    @property
    def jdaviz_helper(self):
        """The Jdaviz configuration helper tied to the viewer."""
        return self.jdaviz_app._jdaviz_helper

    @property
    def hub(self):
        return self.session.hub

    @property
    def reference_id(self):
        return self._reference_id

    @property
    def reference(self):
        return self.jdaviz_app._viewer_item_by_id(self.reference_id).get('reference')

    @property
    def _ref_or_id(self):
        reference = self.reference
        if reference is not None:
            return reference
        return self.reference_id

    def set_plot_axes(self):
        # individual viewers can override to set custom axes labels/ticks/styling
        return
