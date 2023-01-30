import os

from traitlets import Any, Dict, Float, Bool, Int, List, Unicode, observe

from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.viewers.image.state import ImageSubsetLayerState
from glue_jupyter.bqplot.image.state import BqplotImageLayerState
from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelect, LayerSelect,
                                        PlotOptionsSyncState)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR

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
    """
    template_file = __file__, "plot_options.vue"

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

    # image viewer/layer options
    stretch_function_value = Unicode().tag(sync=True)
    stretch_function_sync = Dict().tag(sync=True)

    stretch_preset_value = Any().tag(sync=True)  # glue will pass either a float or string
    stretch_preset_sync = Dict().tag(sync=True)

    stretch_vmin_value = Float().tag(sync=True)
    stretch_vmin_sync = Dict().tag(sync=True)

    stretch_vmax_value = Float().tag(sync=True)
    stretch_vmax_sync = Dict().tag(sync=True)

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

    show_mouseover_marker = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'multiselect')
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected', 'viewer_selected', 'multiselect')  # noqa

        def is_profile(state):
            return isinstance(state, (ProfileViewerState, ProfileLayerState))

        def not_profile(state):
            return not is_profile(state)

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

        # Profile/line viewer/layer options:
        self.line_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                 'line_visible_value', 'line_visible_sync',
                                                 state_filter=is_profile)
        self.collapse_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'function',
                                                      'collapse_func_value', 'collapse_func_sync')
        self.line_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                               'line_color_value', 'line_color_sync',
                                               state_filter=not_image_or_spatial_subset)
        self.line_width = PlotOptionsSyncState(self, self.viewer, self.layer, 'linewidth',
                                               'line_width_value', 'line_width_sync',
                                               state_filter=line_visible)
        self.line_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                 'line_opacity_value', 'line_opacity_sync',
                                                 state_filter=is_profile)
        self.line_as_steps = PlotOptionsSyncState(self, self.viewer, self.layer, 'as_steps',
                                                  'line_as_steps_value', 'line_as_steps_sync')
        self.uncertainty_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_uncertainty',  # noqa
                                                        'uncertainty_visible_value', 'uncertainty_visible_sync')  # noqa

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
        self.show_mouseover_marker = self.app.state.settings['mouseover_marker']
        self.app.state.add_callback('settings', self._on_app_settings_changed)

    @property
    def user_api(self):
        expose = ['multiselect', 'viewer', 'layer', 'select_all', 'subset_visible']
        if self.config == "cubeviz":
            expose += ['collapse_function']
        if self.config != "imviz":
            expose += ['axes_visible', 'line_visible', 'line_color', 'line_width', 'line_opacity',
                       'line_as_steps', 'uncertainty_visible']
        if self.config != "specviz":
            expose += ['subset_color',
                       'stretch_function', 'stretch_preset', 'stretch_vmin', 'stretch_vmax',
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
        self.show_mouseover_marker = value['mouseover_marker']

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
