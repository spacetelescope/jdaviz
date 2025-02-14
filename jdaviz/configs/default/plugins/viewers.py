from echo import delay_callback

import numpy as np

from glue.config import data_translator
from glue.core import BaseData
from glue.core.exceptions import IncompatibleAttribute
from glue.core.units import UnitConverter
from glue.core.subset import Subset
from glue.core.subset_group import GroupedSubset
from glue.viewers.scatter.state import ScatterLayerState as BqplotScatterLayerState

from glue_astronomy.spectral_coordinates import SpectralCoordinates
from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer

from astropy.utils import deprecated
from astropy import units as u
from astropy.nddata import (
    NDDataArray, StdDevUncertainty, VarianceUncertainty, InverseVariance
)
from specutils import Spectrum1D

from jdaviz.components.toolbar_nested import NestedJupyterToolbar
from jdaviz.configs.default.plugins.data_menu import DataMenu
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.custom_units_and_equivs import _eqv_sb_per_pixel_to_per_angle
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.core.marks import LineUncertainties, ScatterMask, OffscreenLinesMarks
from jdaviz.core.registries import viewer_registry
from jdaviz.core.template_mixin import WithCache
from jdaviz.core.user_api import ViewerUserApi
from jdaviz.core.unit_conversion_utils import check_if_unit_is_per_solid_angle
from jdaviz.utils import (ColorCycler, get_subset_type, _wcs_only_label,
                          layer_is_image_data, layer_is_not_dq)

uc = UnitConverter()

uncertainty_str_to_cls_mapping = {
    "std": StdDevUncertainty,
    "var": VarianceUncertainty,
    "ivar": InverseVariance
}


__all__ = ['JdavizViewerMixin', 'JdavizProfileView']

viewer_registry.add("g-profile-viewer", label="Profile 1D", cls=BqplotProfileView)
viewer_registry.add("g-image-viewer", label="Image 2D", cls=BqplotImageView)
viewer_registry.add("g-table-viewer", label="Table", cls=TableViewer)


class JdavizViewerMixin(WithCache):
    toolbar = None
    tools_nested = []
    _prev_limits = None
    _native_mark_classnames = ('Lines', 'LinesGL', 'FRBImage', 'Contour')

    def __init__(self, *args, **kwargs):
        # NOTE: anything here most likely won't be called by viewers because of inheritance order
        super().__init__(*args, **kwargs)

        # Allow each viewer to cycle through colors for each new addition to the viewer:
        self.color_cycler = ColorCycler()

        self._data_menu = DataMenu(viewer=self, app=self.jdaviz_app)

    @property
    def user_api(self):
        # default exposed user APIs.  Can override this method in any particular viewer.
        if not isinstance(self, TableViewer):
            # TODO: eventually remove data_labels_loaded
            # and data_labels_visible once deprecation period passes
            expose = ['data_labels_loaded', 'data_labels_visible', 'data_menu']
        else:
            expose = []
        if isinstance(self, BqplotImageView):
            if isinstance(self, AstrowidgetsImageViewerMixin):
                expose += ['save',
                           'center_on', 'offset_by', 'zoom_level', 'zoom',
                           'colormap_options', 'set_colormap',
                           'stretch_options', 'stretch',
                           'autocut_options', 'cuts',
                           'marker', 'add_markers', 'remove_markers', 'reset_markers',
                           'blink_once', 'reset_limits']
            else:
                # cubeviz image viewers don't inherit from AstrowidgetsImageViewerMixin yet,
                # but also shouldn't expose set_limits because of equal aspect ratio concerns
                expose += []
        elif isinstance(self, TableViewer):
            expose += []
        else:
            expose += ['set_limits', 'reset_limits', 'set_tick_format']
        return ViewerUserApi(self, expose=expose)

    @property
    def data_menu(self):
        return self._data_menu.user_api

    def _deprecated_data_menu(self):
        # temporary method to allow for opening new data-menu from old button.  This should
        # be removed anytime after the old button is removed (likely in 4.3)
        self.data_menu.open_menu()

    @property
    @deprecated(since="4.1", alternative="viewer.data_menu.data_labels_loaded")
    def data_labels_loaded(self):
        """
        List of data labels loaded in this viewer.

        Returns
        -------
        data_labels : list
            list of strings
        """
        return self.data_menu.data_labels_loaded

    @property
    @deprecated(since="4.1", alternative="viewer.data_menu.data_labels_visible")
    def data_labels_visible(self):
        """
        List of data labels visible in this viewer.

        Returns
        -------
        data_labels : list
            list of strings
        """
        return self.data_menu.data_labels_visible

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
            if val is not None and not isinstance(val, (float, int, np.float32)):
                raise TypeError('All arguments must be None, int, or float, '
                                f'but got: {type(val)}')

        with delay_callback(self.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            if x_min is not None:
                self.state.x_min = x_min
            if x_max is not None:
                self.state.x_max = x_max
            # NOTE: for some reason, setting ymax first avoids an issue
            # where back-to-back calls of get_limits and set_limits
            # give different results for y limits.
            if y_max is not None:
                self.state.y_max = y_max
            if y_min is not None:
                self.state.y_min = y_min

    def get_limits(self):
        """Return current viewer axes limits.

        Returns
        -------
        x_min, x_max, y_min, y_max : float
            Lower/upper X/Y limits, respectively.

        """
        return self.state.x_min, self.state.x_max, self.state.y_min, self.state.y_max

    def set_tick_format(self, fmt, axis):
        """
        Manually set the tick format of one of the axes.

        Parameters
        ----------
        fmt : str
            Format of tick marks.
            For example, ``'0.1e'`` to set scientific notation or ``'0.2f'`` to turn it off.
        axis : {x, y}
            The viewer axis.
        """
        if axis not in ('x', 'y'):
            raise ValueError("axis must be 'x' or 'y'")
        # Examples of values for fmt are '0.1e' or '0.2f'
        axis = {'x': 0, 'y': 1}[axis]
        self.figure.axes[axis].tick_format = fmt

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
        if self.__class__.__name__ == 'RampvizImageView':
            # Do not override default for subsets as for some reason
            # this isn't getting called when they're first added, but rather when
            # the next state change is made (for example: manually changing the visibility)
            return

        # default visibility based on the visibility of the "parent" data layer
        if self.__class__.__name__ == 'RampvizProfileView':
            # Rampviz doesn't show subset profiles by default:
            layer_state.visible = False
        elif (self.__class__.__name__ == 'CubevizImageView' and
              get_subset_type(layer_state.layer) != 'spatial'):
            # set visibility of spectral subsets to false in Cubeviz image-viewers
            layer_state.visible = False
        else:
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
            if 'Trace' in layer.layer.data.meta:
                return "mdi-chart-line-stacked", None

            for subset in self.jdaviz_app.data_collection.subset_groups:
                if subset.label == layer.layer.label:
                    subset_type = get_subset_type(subset)
                    if subset_type == 'spatial':
                        return "mdi-chart-scatter-plot", subset_type
                    else:
                        return "mdi-chart-bell-curve", subset_type
            return "", None

        visible_layers = {}
        for layer in self.state.layers[::-1]:
            layer_is_wcs_only = (
                    hasattr(layer.layer, 'meta') and
                    layer.layer.meta.get(_wcs_only_label, False)
            )
            if layer.visible and not layer_is_wcs_only:
                prefix_icon, subset_type = _get_layer_info(layer)
                if (
                    subset_type == 'spatial' and
                    self.__class__.__name__ in ('CubevizProfileView', 'RampvizProfileView')
                ):
                    # do not show spatial subsets in profile viewer
                    continue
                visible_layers[layer.layer.label] = {'color': _get_layer_color(layer),
                                                     'linewidth': _get_layer_linewidth(layer),
                                                     'prefix_icon': prefix_icon}

        self._data_menu.visible_layers = visible_layers

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
                          if (layer.visible and
                              layer_is_image_data(layer.layer) and
                              layer_is_not_dq(layer.layer) and
                              (layer.bitmap_visible or layer.contour_visible))]
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


@viewer_registry("jdaviz-profile-viewer", label="Profile 1D")
class JdavizProfileView(JdavizViewerMixin, BqplotProfileView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _state_cls = FreezableProfileViewerState
    _default_profile_subset_type = None

    def __init__(self, *args, **kwargs):
        default_tool_priority = kwargs.pop('default_tool_priority', [])
        super().__init__(*args, **kwargs)

        self._subscribe_to_layers_update()
        self.initialize_toolbar(default_tool_priority=default_tool_priority)
        self._offscreen_lines_marks = OffscreenLinesMarks(self)
        self.figure.marks = self.figure.marks + self._offscreen_lines_marks.marks

        self.state.add_callback('show_uncertainty', self._show_uncertainty_changed)

        self.display_mask = False

        # Change collapse function to sum
        default_collapse_function = kwargs.pop('default_collapse_function', 'sum')

        self.state.function = default_collapse_function

    def _expected_subset_layer_default(self, layer_state):
        super()._expected_subset_layer_default(layer_state)

        layer_state.linewidth = 3

    def data(self, cls=None):
        # Grab the user's chosen statistic for collapsing data
        statistic = getattr(self.state, 'function', None)
        data = []

        for layer_state in self.state.layers:
            if hasattr(layer_state, 'layer'):
                lyr = layer_state.layer

                # For raw data, just include the data itself
                if isinstance(lyr, BaseData):
                    _class = cls or self.default_class

                    if _class is not None:
                        cache_key = (lyr.label, statistic)
                        if cache_key in self.jdaviz_app._get_object_cache:
                            layer_data = self.jdaviz_app._get_object_cache[cache_key]
                        else:
                            # If spectrum, collapse via the defined statistic
                            if _class == Spectrum1D:
                                layer_data = lyr.get_object(cls=_class, statistic=statistic)
                            else:
                                layer_data = lyr.get_object(cls=_class)
                            self.jdaviz_app._get_object_cache[cache_key] = layer_data

                        data.append(layer_data)

                # For subsets, make sure to apply the subset mask to the layer data first
                elif isinstance(lyr, Subset):
                    layer_data = lyr

                    if _class is not None:
                        handler, _ = data_translator.get_handler_for(_class)
                        try:
                            layer_data = handler.to_object(layer_data, statistic=statistic)
                        except IncompatibleAttribute:
                            continue
                    data.append(layer_data)

        return data

    def get_scales(self):
        fig = self.figure
        # Deselect any pan/zoom or subsetting tools so they don't interfere
        # with the scale retrieval
        if self.toolbar.active_tool is not None:
            self.toolbar.active_tool = None
        return {'x': fig.interaction.x_scale, 'y': fig.interaction.y_scale}

    def _show_uncertainty_changed(self, msg=None):
        # this is subscribed in init to watch for changes to the state
        # object since uncertainty handling is in jdaviz instead of glue/glue-jupyter
        if self.state.show_uncertainty:
            self._plot_uncertainties()
        else:
            self._clean_error()

    def show_mask(self):
        self.display_mask = True
        self._plot_mask()

    def clean(self):
        # Remove extra traces, in case they exist.
        self.display_mask = False
        self._clean_mask()

        # this will automatically call _clean_error via _show_uncertainty_changed
        self.state.show_uncertainty = False

    def _clean_mask(self):
        fig = self.figure
        fig.marks = [x for x in fig.marks if not isinstance(x, ScatterMask)]

    def _clean_error(self):
        fig = self.figure
        fig.marks = [x for x in fig.marks if not isinstance(x, LineUncertainties)]

    def add_data(self, data, color=None, alpha=None, **layer_state):
        """
        Overrides the base class to add markers for plotting
        uncertainties and data quality flags.

        Parameters
        ----------
        spectrum : :class:`glue.core.data.Data`
            Data object with the spectrum.
        color : obj
            Color value for plotting.
        alpha : float
            Alpha value for plotting.

        Returns
        -------
        result : bool
            `True` if successful, `False` otherwise.
        """
        # If this is the first loaded data, set things up for unit conversion.
        if len(self.layers) == 0:
            reset_plot_axes = True
        else:
            # Check if the new data flux unit is actually compatible since flux not linked.
            try:
                if self.state.y_display_unit not in ['None', None, 'DN']:
                    uc.to_unit(data, data.find_component_id("flux"), [1, 1],
                               u.Unit(self.state.y_display_unit))  # Error if incompatible
            except Exception as err:
                # Raising exception here introduces a dirty state that messes up next load_data
                # but not raising exception also causes weird behavior unless we remove the data
                # completely.
                self.session.hub.broadcast(SnackbarMessage(
                    f"Failed to load {data.label}, so removed it: {repr(err)}",
                    sender=self, color='error'))
                self.jdaviz_app.data_collection.remove(data)
                return False
            reset_plot_axes = False

        # The base class handles the plotting of the main
        # trace representing the profile itself.
        result = super().add_data(data, color, alpha, **layer_state)

        if reset_plot_axes:
            x_units = data.get_component(self.state.x_att.label).units

            y_axis_component = (
                'flux' if 'flux' in [comp.label for comp in self.state.layers[0].layer.components]
                else 'data'
            )
            y_units = data.get_component(y_axis_component).units
            with delay_callback(self.state, "x_display_unit", "y_display_unit"):
                self.state.x_display_unit = x_units if len(x_units) else None
                self.state.y_display_unit = y_units if len(y_units) else None
            self.set_plot_axes()

        self._plot_uncertainties()

        self._plot_mask()

        # Set default linewidth on any created spectral subset layers
        # NOTE: this logic will need updating if we add support for multiple cubes as this assumes
        # that new data entries (from model fitting or gaussian smooth, etc) will only be spectra
        # and all subsets affected will be spectral
        for layer in self.state.layers:
            if (isinstance(layer.layer, GroupedSubset)
                    and get_subset_type(layer.layer) == self._default_profile_subset_type
                    and layer.layer.data.label == data.label):
                layer.linewidth = 3

        return result

    def _plot_mask(self):
        if not self.display_mask:
            return

        # Remove existing mask marks
        self._clean_mask()

        # Loop through all active data in the viewer
        for index, layer_state in enumerate(self.state.layers):
            lyr = layer_state.layer
            comps = [str(component) for component in lyr.components]

            # Skip subsets
            if hasattr(lyr, "subset_state"):
                continue

            # Ignore data that does not have a mask component
            if "mask" in comps:
                mask = np.array(lyr['mask'].data)

                data_obj = lyr.data.get_object(cls=self.default_class)

                if self.default_class == Spectrum1D:
                    data_x = data_obj.spectral_axis.value
                    data_y = data_obj.flux.value
                else:
                    data_x = np.arange(data_obj.shape[-1])
                    data_y = data_obj.data.value

                # For plotting markers only for the masked data
                # points, erase un-masked data from trace.
                y = np.where(np.asarray(mask) == 0, np.nan, data_y)

                # A subclass of the bqplot Scatter object, ScatterMask places
                # 'X' marks where there is masked data in the viewer.
                color = layer_state.color
                alpha_shade = layer_state.alpha / 3
                mask_line_mark = ScatterMask(scales=self.scales,
                                             marker='cross',
                                             x=data_x,
                                             y=y,
                                             stroke_width=0.5,
                                             colors=[color],
                                             default_size=25,
                                             default_opacities=[alpha_shade]
                                             )
                # Add mask marks to viewer
                self.figure.marks = list(self.figure.marks) + [mask_line_mark]

    def _plot_uncertainties(self):
        if not self.state.show_uncertainty:
            return

        # Remove existing error bars
        self._clean_error()

        # Loop through all active data in the viewer
        for index, layer_state in enumerate(self.state.layers):
            lyr = layer_state.layer

            # Skip subsets
            if hasattr(lyr, "subset_state"):
                continue

            comps = [str(component) for component in lyr.components]

            # Ignore data that does not have an uncertainty component
            if "uncertainty" in comps:  # noqa
                error = np.array(lyr['uncertainty'].data)

                # ensure that the uncertainties are represented as stddev:
                uncertainty_type_str = lyr.meta.get('uncertainty_type', 'stddev')
                uncert_cls = uncertainty_str_to_cls_mapping[uncertainty_type_str]
                error = uncert_cls(error).represent_as(StdDevUncertainty).array

                # Then we assume that last axis is always wavelength.
                # This may need adjustment after the following
                # specutils PR is merged: https://github.com/astropy/specutils/pull/1033
                spectral_axis = -1
                data_obj = lyr.data.get_object(cls=self.default_class, statistic=None)

                if isinstance(lyr.data.coords, SpectralCoordinates):
                    spectral_wcs = lyr.data.coords
                    data_x = spectral_wcs.pixel_to_world_values(
                        np.arange(lyr.data.shape[spectral_axis])
                    )
                    if isinstance(data_x, tuple):
                        data_x = data_x[0]
                else:
                    if hasattr(lyr.data.coords, 'spectral_wcs'):
                        spectral_wcs = lyr.data.coords.spectral_wcs
                    elif hasattr(lyr.data.coords, 'spectral'):
                        spectral_wcs = lyr.data.coords.spectral
                    data_x = spectral_wcs.pixel_to_world(
                        np.arange(lyr.data.shape[spectral_axis])
                    )

                data_y = data_obj.data

                # The shaded band around the spectrum trace is bounded by
                # two lines, above and below the spectrum trace itself.
                data_x_list = np.ndarray.tolist(data_x)
                x = [data_x_list, data_x_list]
                y = [np.ndarray.tolist(data_y - error),
                     np.ndarray.tolist(data_y + error)]

                if layer_state.as_steps:
                    for i in (0, 1):
                        a = np.insert(x[i], 0, 2*x[i][0] - x[i][1])
                        b = np.append(x[i], 2*x[i][-1] - x[i][-2])
                        edges = (a + b) / 2
                        x[i] = np.concatenate((edges[:1], np.repeat(edges[1:-1], 2), edges[-1:]))
                        y[i] = np.repeat(y[i], 2)
                x, y = np.asarray(x), np.asarray(y)

                # A subclass of the bqplot Lines object, LineUncertainties keeps
                # track of uncertainties plotted in the viewer. LineUncertainties
                # appear with two lines and shaded area in between.
                color = layer_state.color
                alpha_shade = layer_state.alpha / 3
                error_line_mark = LineUncertainties(viewer=self,
                                                    x=[x],
                                                    y=[y],
                                                    scales=self.scales,
                                                    stroke_width=1,
                                                    colors=[color, color],
                                                    fill_colors=[color, color],
                                                    opacities=[0.0, 0.0],
                                                    fill_opacities=[alpha_shade,
                                                                    alpha_shade],
                                                    fill='between',
                                                    close_path=False
                                                    )

                # Add error lines to viewer
                self.figure.marks = list(self.figure.marks) + [error_line_mark]

    def set_plot_axes(self):
        # Set x and y axes labels for the spectrum viewer
        y_display_unit = self.state.y_display_unit
        y_unit = (
            u.Unit(y_display_unit) if y_display_unit and y_display_unit != 'None'
            else u.dimensionless_unscaled
        )

        # Get local units.
        locally_defined_flux_units = [
            u.Jy, u.mJy, u.uJy, u.MJy,
            u.W / (u.m**2 * u.Hz),
            u.eV / (u.s * u.m**2 * u.Hz),
            u.erg / (u.s * u.cm**2),
            u.erg / (u.s * u.cm**2 * u.Angstrom),
            u.erg / (u.s * u.cm**2 * u.Hz),
            u.ph / (u.s * u.cm**2 * u.Angstrom),
            u.ph / (u.s * u.cm**2 * u.Hz),
            u.bol, u.AB, u.ST
        ]

        # get square angle from 'sb' display unit
        sb_unit = self.jdaviz_app._get_display_unit(axis='sb')
        if sb_unit is not None:
            solid_angle_unit = check_if_unit_is_per_solid_angle(sb_unit, return_unit=True)
        else:
            solid_angle_unit = None

        # if solid angle is present in denominator, check physical type of numerator
        # if numerator is a flux type the display unit is a 'surface brightness', otherwise
        # default to the catchall 'flux density' label
        flux_unit_type = None

        for un in locally_defined_flux_units:
            locally_defined_sb_unit = un / solid_angle_unit if solid_angle_unit is not None else None  # noqa

            # create an equivalency for each flux unit for flux <> flux/pix2.
            # for similar reasons to the 'untranslatable units' issue, custom
            # equivs. can't be combined, so a workaround is creating an eqiv
            # for each flux that may need an additional equiv.
            angle_to_pixel_equiv = _eqv_sb_per_pixel_to_per_angle(un)

            if (locally_defined_sb_unit is not None
                    and y_unit.is_equivalent(locally_defined_sb_unit, angle_to_pixel_equiv)):
                flux_unit_type = "Surface Brightness"
            elif y_unit.is_equivalent(un):
                flux_unit_type = 'Flux'
            elif y_unit.is_equivalent(u.electron / u.s) or y_unit.physical_type == 'dimensionless':  # noqa
                # electron / s or 'dimensionless_unscaled' should be labeled counts
                flux_unit_type = "Counts"
            elif y_unit.is_equivalent(u.W):
                flux_unit_type = "Luminosity"
            if flux_unit_type is not None:
                # if we determined a label, stop checking
                break
        else:
            # default to Flux Density for flux density or uncaught types
            flux_unit_type = "Flux density"

        # Set x axes labels for the spectrum viewer
        x_disp_unit = self.state.x_display_unit
        x_unit = u.Unit(x_disp_unit) if x_disp_unit else u.dimensionless_unscaled

        if x_unit.is_equivalent(u.m):
            spectral_axis_unit_type = "Wavelength"
        elif x_unit.is_equivalent(u.Hz):
            spectral_axis_unit_type = "Frequency"
        elif x_unit.is_equivalent(u.pixel):
            spectral_axis_unit_type = "Pixel"
        elif x_unit.is_equivalent(u.dimensionless_unscaled):
            # case for rampviz
            spectral_axis_unit_type = "Group"
        else:
            spectral_axis_unit_type = str(x_unit.physical_type).title()

        with self.figure.hold_sync():
            self.figure.axes[0].label = f"{spectral_axis_unit_type}" + (
                f" [{self.state.x_display_unit}]"
                if self.state.x_display_unit not in ["None", None] else ""
            )
            self.figure.axes[1].label = f"{flux_unit_type}" + (
                f"[{self.state.y_display_unit}]"
                if self.state.y_display_unit not in ["None", None] else ""
            )

            # Make it so axis labels are not covering tick numbers.
            self.figure.fig_margin["left"] = 95
            self.figure.fig_margin["bottom"] = 60
            self.figure.send_state('fig_margin')  # Force update
            self.figure.axes[0].label_offset = "40"
            self.figure.axes[1].label_offset = "-70"
            # NOTE: with tick_style changed below, the default responsive ticks in bqplot result
            # in overlapping tick labels.  For now we'll hardcode at 8, but this could be removed
            # (default to None) if/when bqplot auto ticks react to styling options.
            self.figure.axes[1].num_ticks = 8

            # Set Y-axis to scientific notation
            self.figure.axes[1].tick_format = '0.1e'

            for i in (0, 1):
                self.figure.axes[i].tick_style = {'font-size': 15, 'font-weight': 600}
