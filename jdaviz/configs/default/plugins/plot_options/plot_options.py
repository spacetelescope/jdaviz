import os
import bqplot
import numpy as np

from astropy.visualization import PercentileInterval
from ipywidgets import widget_serialization
from traitlets import Any, Dict, Float, Bool, Int, List, Unicode, observe

from glue.viewers.scatter.state import ScatterViewerState
from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.viewers.image.state import ImageSubsetLayerState
from glue_jupyter.bqplot.scatter.layer_artist import BqplotScatterLayerState
from glue_jupyter.bqplot.image.state import BqplotImageLayerState
from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelect, LayerSelect,
                                        PlotOptionsSyncState)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.utils import bqplot_clear_figure
from jdaviz.core.marks import HistogramMark

__all__ = ['PlotOptions']


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(PluginTemplateMixin):
    """
    The Plot Options Plugin gives access to per-viewer and per-layer options and enables
    setting across multiple viewers/layers simultaneously.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``multiselect``:
      whether ``viewer`` and ``layer`` should both be in multiselect mode.
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
    * ``layer`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
    * :meth:`select_all`
    * ``subset_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      whether a subset should be visible.
    * ``subset_color`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``axes_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``collapse_function`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      only exposed for Cubeviz
    * ``line_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``line_color`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``line_width`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``line_opacity`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``line_as_steps`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``uncertainty_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
    * ``stretch_function`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``stretch_preset`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``stretch_vmin`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``stretch_vmax`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``stretch_hist_zoom_limits`` : whether to show the histogram for the current zoom
      limits instead of all data within the layer; not exposed for Specviz.
    * ``image_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      whether the image bitmap is visible; not exposed for Specviz.
    * ``image_color_mode`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``image_color`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz.  This only applies when ``image_color_mode`` is "Monochromatic".
    * ``image_colormap`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. This only applies when ``image_color_mode`` is "Colormap".
    * ``image_opacity`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. Valid values are between 0 and 1, inclusive. Default is 1.
    * ``image_contrast`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. Valid values are between 0 and 4, inclusive. Default is 1.
    * ``image_bias`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. Valid values are between 0 and 1, inclusive. Default is 0.5.
    * ``contour_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      whether the contour is visible; not exposed for Specviz
    * ``contour_mode`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``contour_min`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. This only applies when ``contour_mode`` is "Linear".
    * ``contour_max`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. This only applies when ``contour_mode`` is "Linear".
    * ``contour_nlevels`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. This only applies when ``contour_mode`` is "Linear".
    * ``contour_custom_levels`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz. This only applies when ``contour_mode`` is "Custom".
    * :meth: `set_histogram_nbins`
    """
    template_file = __file__, "plot_options.vue"
    uses_active_status = Bool(True).tag(sync=True)

    # multiselect is shared between viewer and layer
    multiselect = Bool(False).tag(sync=True)

    viewer_items = List().tag(sync=True)
    viewer_selected = Any().tag(sync=True)  # Any needed for multiselect
    layer_items = List().tag(sync=True)
    layer_selected = Any().tag(sync=True)  # Any needed for multiselect

    # profile/line viewer/layer options:
    line_visible_value = Bool().tag(sync=True)
    line_visible_sync = Dict().tag(sync=True)

    collapse_func_value = Unicode().tag(sync=True)
    collapse_func_sync = Dict().tag(sync=True)

    line_color_value = Any().tag(sync=True)
    line_color_sync = Dict().tag(sync=True)

    line_width_value = Int().tag(sync=True)
    line_width_sync = Dict().tag(sync=True)

    line_opacity_value = Float().tag(sync=True)
    line_opacity_sync = Dict().tag(sync=True)

    line_as_steps_value = Bool().tag(sync=True)
    line_as_steps_sync = Dict().tag(sync=True)

    uncertainty_visible_value = Int().tag(sync=True)
    uncertainty_visible_sync = Dict().tag(sync=True)

    # scatter/marker options
    marker_visible_value = Bool().tag(sync=True)
    marker_visible_sync = Dict().tag(sync=True)

    marker_fill_value = Bool().tag(sync=True)
    marker_fill_sync = Dict().tag(sync=True)

    marker_opacity_value = Float().tag(sync=True)
    marker_opacity_sync = Dict().tag(sync=True)

    marker_size_mode_value = Unicode().tag(sync=True)
    marker_size_mode_sync = Dict().tag(sync=True)

    marker_size_value = Float().tag(sync=True)
    marker_size_sync = Dict().tag(sync=True)

    marker_size_scale_value = Float().tag(sync=True)
    marker_size_scale_sync = Dict().tag(sync=True)

    marker_size_col_value = Unicode().tag(sync=True)
    marker_size_col_sync = Dict().tag(sync=True)

    marker_size_vmin_value = Float().tag(sync=True)
    marker_size_vmin_sync = Dict().tag(sync=True)

    marker_size_vmax_value = Float().tag(sync=True)
    marker_size_vmax_sync = Dict().tag(sync=True)

    marker_color_mode_value = Unicode().tag(sync=True)
    marker_color_mode_sync = Dict().tag(sync=True)

    marker_color_value = Any().tag(sync=True)
    marker_color_sync = Dict().tag(sync=True)

    marker_color_col_value = Unicode().tag(sync=True)
    marker_color_col_sync = Dict().tag(sync=True)

    marker_colormap_value = Unicode().tag(sync=True)
    marker_colormap_sync = Dict().tag(sync=True)

    marker_colormap_vmin_value = Float().tag(sync=True)
    marker_colormap_vmin_sync = Dict().tag(sync=True)

    marker_colormap_vmax_value = Float().tag(sync=True)
    marker_colormap_vmax_sync = Dict().tag(sync=True)

    # image viewer/layer options
    stretch_function_value = Unicode().tag(sync=True)
    stretch_function_sync = Dict().tag(sync=True)

    stretch_preset_value = Any().tag(sync=True)  # glue will pass either a float or string
    stretch_preset_sync = Dict().tag(sync=True)

    stretch_vmin_value = Float().tag(sync=True)
    stretch_vmin_sync = Dict().tag(sync=True)

    stretch_vmax_value = Float().tag(sync=True)
    stretch_vmax_sync = Dict().tag(sync=True)

    stretch_hist_zoom_limits = Bool().tag(sync=True)
    stretch_hist_nbins = IntHandleEmpty().tag(sync=True)
    stretch_histogram = Any().tag(sync=True, **widget_serialization)

    subset_visible_value = Bool().tag(sync=True)
    subset_visible_sync = Dict().tag(sync=True)

    subset_color_value = Unicode().tag(sync=True)
    subset_color_sync = Dict().tag(sync=True)

    image_visible_value = Bool().tag(sync=True)
    image_visible_sync = Dict().tag(sync=True)

    image_color_mode_value = Unicode().tag(sync=True)
    image_color_mode_sync = Dict().tag(sync=True)

    image_color_value = Any().tag(sync=True)
    image_color_sync = Dict().tag(sync=True)

    image_colormap_value = Unicode().tag(sync=True)
    image_colormap_sync = Dict().tag(sync=True)

    image_opacity_value = Float().tag(sync=True)
    image_opacity_sync = Dict().tag(sync=True)

    image_contrast_value = Float().tag(sync=True)
    image_contrast_sync = Dict().tag(sync=True)

    image_bias_value = Float().tag(sync=True)
    image_bias_sync = Dict().tag(sync=True)

    contour_spinner = Bool().tag(sync=True)

    contour_visible_value = Bool().tag(sync=True)
    contour_visible_sync = Dict().tag(sync=True)

    contour_mode_value = Unicode().tag(sync=True)
    contour_mode_sync = Dict().tag(sync=True)

    contour_min_value = Float().tag(sync=True)
    contour_min_sync = Dict().tag(sync=True)

    contour_max_value = Float().tag(sync=True)
    contour_max_sync = Dict().tag(sync=True)

    contour_nlevels_value = Int().tag(sync=True)
    contour_nlevels_sync = Dict().tag(sync=True)

    contour_custom_levels_value = List().tag(sync=True)
    contour_custom_levels_txt = Unicode().tag(sync=True)   # controlled by vue
    contour_custom_levels_sync = Dict().tag(sync=True)

    axes_visible_value = Bool().tag(sync=True)
    axes_visible_sync = Dict().tag(sync=True)

    icon_radialtocheck = Unicode(read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml')).tag(sync=True)  # noqa
    icon_checktoradial = Unicode(read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')).tag(sync=True)  # noqa

    show_viewer_labels = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'multiselect')
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected', 'viewer_selected', 'multiselect')  # noqa

        def is_profile(state):
            return isinstance(state, (ProfileViewerState, ProfileLayerState))

        def not_profile(state):
            return not is_profile(state)

        def is_scatter(state):
            return isinstance(state, (ScatterViewerState, BqplotScatterLayerState))

        def supports_line(state):
            return is_profile(state) or is_scatter(state)

        def is_image(state):
            return isinstance(state, BqplotImageLayerState)

        def not_image(state):
            return not is_image(state)

        def not_image_or_spatial_subset(state):
            return not is_image(state) and not is_spatial_subset(state)

        def is_spatial_subset(state):
            return isinstance(state, ImageSubsetLayerState)

        def is_not_subset(state):
            return not is_spatial_subset(state)

        def line_visible(state):
            # exclude for scatter layers where the marker is shown instead of the line
            return getattr(state, 'line_visible', True)

        def state_attr_for_line_visible(state):
            if is_scatter(state):
                return 'line_visible'
            return 'visible'

        # Profile/line viewer/layer options:
        # TODO: once lines are supported in ScatterViewer, update state_filter to supports_line
        self.line_visible = PlotOptionsSyncState(self, self.viewer, self.layer, state_attr_for_line_visible,  # noqa
                                                 'line_visible_value', 'line_visible_sync',
                                                 state_filter=is_profile)
        self.collapse_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'function',
                                                      'collapse_func_value', 'collapse_func_sync')
        self.line_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                               'line_color_value', 'line_color_sync',
                                               state_filter=not_image_or_spatial_subset)
        self.line_width = PlotOptionsSyncState(self, self.viewer, self.layer, 'linewidth',
                                               'line_width_value', 'line_width_sync',
                                               state_filter=supports_line)
        self.line_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                 'line_opacity_value', 'line_opacity_sync',
                                                 state_filter=supports_line)
        self.line_as_steps = PlotOptionsSyncState(self, self.viewer, self.layer, 'as_steps',
                                                  'line_as_steps_value', 'line_as_steps_sync')
        self.uncertainty_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_uncertainty',  # noqa
                                                        'uncertainty_visible_value', 'uncertainty_visible_sync')  # noqa

        # Scatter/marker options:
        self.marker_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                   'marker_visible_value', 'marker_visible_sync',
                                                   state_filter=is_scatter)
        self.marker_fill = PlotOptionsSyncState(self, self.viewer, self.layer, 'fill',
                                                'marker_fill_value', 'marker_fill_sync',
                                                state_filter=is_scatter)
        self.marker_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                   'marker_opacity_value', 'marker_opacity_sync',
                                                   state_filter=is_scatter)
        self.marker_size_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'size_mode',
                                                     'marker_size_mode_value', 'marker_size_mode_sync',  # noqa
                                                     state_filter=is_scatter)
        self.marker_size = PlotOptionsSyncState(self, self.viewer, self.layer, 'size',
                                                'marker_size_value', 'marker_size_sync',
                                                state_filter=is_scatter)
        self.marker_size_scale = PlotOptionsSyncState(self, self.viewer, self.layer, 'size_scaling',
                                                      'marker_size_scale_value', 'marker_size_scale_sync',  # noqa
                                                      state_filter=is_scatter)
        self.marker_size_col = PlotOptionsSyncState(self, self.viewer, self.layer, 'size_att',
                                                    'marker_size_col_value', 'marker_size_col_sync',
                                                    state_filter=is_scatter)
        self.marker_size_vmin = PlotOptionsSyncState(self, self.viewer, self.layer, 'size_vmin',
                                                     'marker_size_vmin_value', 'marker_size_vmin_sync',  # noqa
                                                     state_filter=is_scatter)
        self.marker_size_vmax = PlotOptionsSyncState(self, self.viewer, self.layer, 'size_vmax',
                                                     'marker_size_vmax_value', 'marker_size_vmax_sync',  # noqa
                                                     state_filter=is_scatter)

        # TODO: remove marker_ prefix if these also apply to the lines?
        self.marker_color_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap_mode',
                                                      'marker_color_mode_value', 'marker_color_mode_sync',  # noqa
                                                      state_filter=is_scatter)
        self.marker_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                                 'marker_color_value', 'marker_color_sync',
                                                 state_filter=is_scatter)
        self.marker_color_col = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap_att',
                                                     'marker_color_col_value', 'marker_color_col_sync',  # noqa
                                                     state_filter=is_scatter)
        self.marker_colormap = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap',
                                                    'marker_colormap_value', 'marker_colormap_sync',
                                                    state_filter=is_scatter)
        self.marker_colormap_vmin = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap_vmin',
                                                         'marker_colormap_vmin_value', 'marker_colormap_vmin_sync',  # noqa
                                                         state_filter=is_scatter)
        self.marker_colormap_vmax = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap_vmax',
                                                         'marker_colormap_vmax_value', 'marker_colormap_vmax_sync',  # noqa
                                                         state_filter=is_scatter)

        # Image viewer/layer options:
        self.stretch_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'stretch',
                                                     'stretch_function_value', 'stretch_function_sync',  # noqa
                                                     state_filter=is_image)
        self.stretch_preset = PlotOptionsSyncState(self, self.viewer, self.layer, 'percentile',
                                                   'stretch_preset_value', 'stretch_preset_sync',
                                                   state_filter=is_image)
        self.stretch_vmin = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_min',
                                                 'stretch_vmin_value', 'stretch_vmin_sync',
                                                 state_filter=is_image)
        self.stretch_vmax = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_max',
                                                 'stretch_vmax_value', 'stretch_vmax_sync',
                                                 state_filter=is_image)

        self.subset_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                   'subset_visible_value', 'subset_visible_sync',
                                                   state_filter=is_spatial_subset)
        self.subset_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                                 'subset_color_value', 'subset_color_sync',
                                                 state_filter=is_spatial_subset)
        self.image_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'bitmap_visible',
                                                  'image_visible_value', 'image_visible_sync',
                                                  state_filter=is_image)
        self.image_color_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'color_mode',  # noqa
                                                     'image_color_mode_value', 'image_color_mode_sync')  # noqa
        self.image_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                                'image_color_value', 'image_color_sync',
                                                state_filter=is_image)
        self.image_colormap = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap',
                                                   'image_colormap_value', 'image_colormap_sync')
        self.image_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                  'image_opacity_value', 'image_opacity_sync',
                                                  state_filter=is_image)
        self.image_contrast = PlotOptionsSyncState(self, self.viewer, self.layer, 'contrast',
                                                   'image_contrast_value', 'image_contrast_sync')
        self.image_bias = PlotOptionsSyncState(self, self.viewer, self.layer, 'bias',
                                               'image_bias_value', 'image_bias_sync')

        self.contour_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'contour_visible',  # noqa
                                                    'contour_visible_value', 'contour_visible_sync',
                                                    spinner='contour_spinner')
        self.contour_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'level_mode',
                                                 'contour_mode_value', 'contour_mode_sync',
                                                 spinner='contour_spinner')
        self.contour_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_min',
                                                'contour_min_value', 'contour_min_sync',
                                                spinner='contour_spinner')
        self.contour_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_max',
                                                'contour_max_value', 'contour_max_sync',
                                                spinner='contour_spinner')
        self.contour_nlevels = PlotOptionsSyncState(self, self.viewer, self.layer, 'n_levels',
                                                    'contour_nlevels_value', 'contour_nlevels_sync',
                                                    spinner='contour_spinner')
        self.contour_custom_levels = PlotOptionsSyncState(self, self.viewer, self.layer, 'levels',
                                                          'contour_custom_levels_value', 'contour_custom_levels_sync',   # noqa
                                                          spinner='contour_spinner')

        # Axes options:
        # axes_visible hidden for imviz in plot_options.vue
        self.axes_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_axes',
                                                 'axes_visible_value', 'axes_visible_sync',
                                                 state_filter=not_profile)
        # zoom limits
        # display_units

        self.show_viewer_labels = self.app.state.settings['viewer_labels']
        self.app.state.add_callback('settings', self._on_app_settings_changed)

    @property
    def user_api(self):
        expose = ['multiselect', 'viewer', 'layer', 'select_all', 'subset_visible',
                  'set_histogram_nbins']
        if self.config == "cubeviz":
            expose += ['collapse_function']
        if self.config != "imviz":
            expose += ['axes_visible', 'line_visible', 'line_color', 'line_width', 'line_opacity',
                       'line_as_steps', 'uncertainty_visible']
        if self.config != "specviz":
            expose += ['subset_color',
                       'stretch_function', 'stretch_preset', 'stretch_vmin', 'stretch_vmax',
                       'stretch_hist_zoom_limits',
                       'image_visible', 'image_color_mode',
                       'image_color', 'image_colormap', 'image_opacity',
                       'image_contrast', 'image_bias',
                       'contour_visible', 'contour_mode',
                       'contour_min', 'contour_max', 'contour_nlevels', 'contour_custom_levels']

        return PluginUserApi(self, expose)

    @observe('show_viewer_labels')
    def _on_show_viewer_labels_changed(self, event):
        self.app.state.settings['viewer_labels'] = event['new']

    def _on_app_settings_changed(self, value):
        self.show_viewer_labels = value['viewer_labels']

    def select_all(self, viewers=True, layers=True):
        """
        Enable multiselect mode and select all viewers and/or layers.

        Parameters
        ----------
        viewers : bool
            Whether to select all viewers (default: True)

        layers: bool
            Whether to select all layers (default: True)
        """
        self.multiselect = True
        if viewers:
            self.viewer.select_all()
        if layers:
            self.layer.select_all()

    def vue_unmix_state(self, name):
        sync_state = getattr(self, name)
        sync_state.unmix_state()

    def vue_set_value(self, data):
        attr_name = data.get('name')
        value = data.get('value')
        setattr(self, attr_name, value)

    @observe('is_active', 'layer_selected', 'viewer_selected',
             'stretch_hist_zoom_limits')
    def _update_stretch_histogram(self, msg={}):
        # Import here to prevent circular import.
        from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
        from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView

        if not self.stretch_function_sync.get('in_subscribed_states'):  # pragma: no cover
            # no (image) viewer with stretch function options
            return
        if not hasattr(self, 'viewer'):  # pragma: no cover
            # plugin hasn't been fully initialized yet
            return
        if (not self.is_active
                or not self.viewer.selected
                or not self.layer.selected):  # pragma: no cover
            # no need to make updates, updates will be redrawn when plugin is opened
            # NOTE: this won't update when the plugin is shown but not open in the tray
            return
        if not isinstance(msg, dict) and not self.stretch_hist_zoom_limits:  # pragma: no cover
            # then this is from the limits callbacks and we don't want to waste resources
            # IMPORTANT: this assumes the only non-observe callback to this method comes
            # from state callbacks from zoom limits.
            return

        if self.multiselect and (len(self.viewer.selected) > 1
                                 or len(self.layer.selected) > 1):  # pragma: no cover
            # currently only support single-layer/viewer.  For now we'll just clear and return.
            # TODO: add support for multi-layer/viewer
            bqplot_clear_figure(self.stretch_histogram)
            return

        if not isinstance(self.viewer.selected_obj, (ImvizImageView, CubevizImageView)):
            # don't update histogram if selected viewer is not an image viewer:
            return

        viewer = self.viewer.selected_obj[0] if self.multiselect else self.viewer.selected_obj

        # manage viewer zoom limit callbacks
        if ((isinstance(msg, dict) and msg.get('name') == 'viewer_selected')
                or not self.stretch_hist_zoom_limits):
            vs = viewer.state
            for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
                vs.add_callback(attr, self._update_stretch_histogram)
        if isinstance(msg, dict) and msg.get('name') == 'viewer_selected':
            viewer_label_old = msg.get('old')[0] if self.multiselect else msg.get('old')
            if len(viewer_label_old):
                vs_old = self.app.get_viewer(viewer_label_old).state
                for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
                    vs_old.remove_callback(attr, self._update_stretch_histogram)

        if self.multiselect:
            data = self.layer.selected_obj[0][0].layer
        elif len(self.layer.selected_obj):
            data = self.layer.selected_obj[0].layer
        else:
            # skip further updates if no data are available:
            return

        comp = data.get_component(data.main_components[0])

        if self.stretch_hist_zoom_limits:
            if hasattr(viewer, '_get_zoom_limits'):
                # Viewer limits. This takes account of Imviz linking.
                xy_limits = viewer._get_zoom_limits(data).astype(int)
                x_limits = xy_limits[:, 0]
                y_limits = xy_limits[:, 1]
                x_min = max(x_limits.min(), 0)
                x_max = x_limits.max()
                y_min = max(y_limits.min(), 0)
                y_max = y_limits.max()

                sub_data = comp.data[y_min:y_max, x_min:x_max].ravel()

            else:
                # spectrum-2d-viewer, for example.  We'll assume the viewer
                # limits correspond to the fixed data components from glue
                # and filter directly.
                x_data = data.get_component(data.components[1]).data
                y_data = data.get_component(data.components[0]).data

                inds = np.where((x_data >= viewer.state.x_min) &
                                (x_data <= viewer.state.x_max) &
                                (y_data >= viewer.state.y_min) &
                                (y_data <= viewer.state.y_max))

                sub_data = comp.data[inds].ravel()
        else:
            # include all data, regardless of zoom limits
            sub_data = comp.data.ravel()

        # filter out nans (or else bqplot will fail)
        if np.any(np.isnan(sub_data)):
            sub_data = sub_data[~np.isnan(sub_data)]

        if self.stretch_histogram is None:
            # first time the figure is requested, need to build from scratch
            self.stretch_histogram = bqplot.Figure(padding_y=0)

            hist_x_sc = bqplot.LinearScale()
            hist_y_sc = bqplot.LinearScale()
            # TODO: Let user change the number of bins?
            # TODO: Let user set y-scale to log
            hist_mark = bqplot.Bins(sample=sub_data, bins=25,
                                    density=True, colors="gray",
                                    scales={'x': hist_x_sc,
                                            'y': hist_y_sc})

            self.stretch_histogram.marks = [hist_mark]
            self.stretch_histogram.axes = [bqplot.Axis(scale=hist_x_sc,
                                                       num_ticks=3,
                                                       tick_format='0.1e',
                                                       label='pixel value'),
                                           bqplot.Axis(scale=hist_y_sc,
                                                       num_ticks=2,
                                                       orientation='vertical',
                                                       label='density')]

            self.bqplot_figs_resize = [self.stretch_histogram]
            self.stretch_hist_nbins = 25

        else:
            hist_mark = self.stretch_histogram.marks[0]
            hist_mark.sample = sub_data
            # TODO: Let user change the number of bins?
            # TODO: Let user set y-scale to log

        interval = PercentileInterval(95)
        if len(sub_data) > 0:
            hist_lims = interval.get_limits(sub_data)
            hist_mark.min, hist_mark.max = hist_lims

        self._check_if_v_stretch_changed()

    @observe('stretch_vmin_value', 'stretch_vmax_value')
    def _check_if_v_stretch_changed(self, msg=None):
        self._remove_histogram_marks()
        self._add_histogram_marks()

    def _add_histogram_marks(self):
        if self.stretch_histogram is None:
            return
        scales = {'x': self.stretch_histogram.axes[0].scale, 'y': bqplot.LinearScale()}
        v_stretch_lines = []
        # Set the viewer limits if they are None
        if self.stretch_histogram.axes[0].scale.min is None:
            self.stretch_histogram.axes[0].scale.min = self.stretch_histogram.marks[0].min
        if self.stretch_histogram.axes[0].scale.max is None:
            self.stretch_histogram.axes[0].scale.max = self.stretch_histogram.marks[0].max

        # If the stretch limits are within the viewer limits, draw the HistogramMark
        if self.stretch_vmin.value >= self.stretch_histogram.axes[0].scale.min:
            vmin_lines = HistogramMark(min_max_value=[self.stretch_vmin.value, self.stretch_vmin.value], # noqa
                                       scales=scales)
            v_stretch_lines.append(vmin_lines)
        if self.stretch_vmax.value <= self.stretch_histogram.axes[0].scale.max:
            vmax_lines = HistogramMark(min_max_value=[self.stretch_vmax.value, self.stretch_vmax.value], # noqa
                                       scales=scales)
            v_stretch_lines.append(vmax_lines)
        self.stretch_histogram.marks = self.stretch_histogram.marks + v_stretch_lines

    def _remove_histogram_marks(self):
        if self.stretch_histogram is None:
            return
        self.stretch_histogram.marks = [mark for mark in self.stretch_histogram.marks
                                        if not isinstance(mark, HistogramMark)]

    @observe("stretch_hist_nbins")
    def histogram_nbins_changed(self, msg):
        if self.stretch_histogram is None or msg['new'] == '' or msg['new'] < 1:
            return
        self.set_histogram_nbins(msg['new'])

    def set_histogram_nbins(self, nbins):
        self.stretch_histogram.marks[0].bins = nbins
        self.stretch_hist_nbins = nbins

    def set_histogram_x_limits(self, x_min, x_max):
        if x_min:
            self.stretch_histogram.axes[0].scale.min = x_min
        if x_max:
            self.stretch_histogram.axes[0].scale.max = x_max

    def set_histogram_y_limits(self, y_min, y_max):
        if y_min:
            self.stretch_histogram.axes[1].scale.min = y_min
        if y_max:
            self.stretch_histogram.axes[1].scale.max = y_max
