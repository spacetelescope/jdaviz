from traitlets import Any, Dict, Float, Bool, Int, List, Unicode, observe
from ipywidgets.widgets import widget_serialization

from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
#from glue_jupyter.bqplot.image.state import BqplotImageViewerState

from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (TemplateMixin, ViewerSelect, LayerSelect,
                                        PlotOptionsSyncState)

__all__ = ['PlotOptions']


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin):
    template_file = __file__, "plot_options.vue"

    # multiselect is shared between viewer and layer
    multiselect = Bool(False).tag(sync=True)

    viewer_items = List().tag(sync=True)
    viewer_selected = Any().tag(sync=True)  # Any needed for multiselect
    layer_items = List().tag(sync=True)
    layer_selected = Any().tag(sync=True)  # Any needed for multiselect

    viewer_widget = Any().tag(sync=True, **widget_serialization)
    layer_widget = Any().tag(sync=True, **widget_serialization)

    # spectrum viewer/layer options:
    collapse_func_value = Unicode().tag(sync=True)
    collapse_func_sync = Dict().tag(sync=True)

    line_color_value = Any().tag(sync=True)
    line_color_sync = Dict().tag(sync=True)

    line_width_value = Int().tag(sync=True)
    line_width_sync = Dict().tag(sync=True)

    line_opacity_value = Float().tag(sync=True)
    line_opacity_sync = Dict().tag(sync=True)

    uncertainty_value = Int().tag(sync=True)
    uncertainty_sync = Dict().tag(sync=True)

    # image viewer/layer options
    stretch_value = Unicode().tag(sync=True)
    stretch_sync = Dict().tag(sync=True)

    stretch_perc_value = Any().tag(sync=True)  # glue will pass either a float or string
    stretch_perc_sync = Dict().tag(sync=True)

    stretch_min_value = Float().tag(sync=True)
    stretch_min_sync = Dict().tag(sync=True)

    stretch_max_value = Float().tag(sync=True)
    stretch_max_sync = Dict().tag(sync=True)

    bitmap_visible_value = Bool().tag(sync=True)
    bitmap_visible_sync = Dict().tag(sync=True)

    color_mode_value = Unicode().tag(sync=True)
    color_mode_sync = Dict().tag(sync=True)

    bitmap_color_value = Any().tag(sync=True)
    bitmap_color_sync = Dict().tag(sync=True)

    bitmap_cmap_value = Unicode().tag(sync=True)
    bitmap_cmap_sync = Dict().tag(sync=True)

    bitmap_opacity_value = Float().tag(sync=True)
    bitmap_opacity_sync = Dict().tag(sync=True)

    bitmap_contrast_value = Float().tag(sync=True)
    bitmap_contrast_sync = Dict().tag(sync=True)

    bitmap_bias_value = Float().tag(sync=True)
    bitmap_bias_sync = Dict().tag(sync=True)

    contour_visible_value = Bool().tag(sync=True)
    contour_visible_sync = Dict().tag(sync=True)

    contour_min_value = Float().tag(sync=True)
    contour_min_sync = Dict().tag(sync=True)

    contour_max_value = Float().tag(sync=True)
    contour_max_sync = Dict().tag(sync=True)

    contour_nlevels_value = Int().tag(sync=True)
    contour_nlevels_sync = Dict().tag(sync=True)

    show_axes_value = Bool().tag(sync=True)
    show_axes_sync = Dict().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'multiselect')
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected', 'viewer_selected', 'multiselect')

        def not_profile(state):
            return not isinstance(state, (ProfileViewerState, ProfileLayerState))

        def is_profile(state):
            return isinstance(state, (ProfileViewerState, ProfileLayerState))

        # Spectrum viewer/layer options:
        self.collapse_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'function', 'collapse_func_value', 'collapse_func_sync')
        self.line_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color', 'line_color_value', 'line_color_sync', state_filter=is_profile)
        self.line_width = PlotOptionsSyncState(self, self.viewer, self.layer, 'linewidth', 'line_width_value', 'line_width_sync')
        self.line_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha', 'line_opacity_value', 'line_opacity_sync', state_filter=is_profile)
        self.uncertainty = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_uncertainty', 'uncertainty_value', 'uncertainty_sync')

        # Image viewer/layer options:
        self.stretch = PlotOptionsSyncState(self, self.viewer, self.layer, 'stretch', 'stretch_value', 'stretch_sync', state_filter=not_profile)
        self.stretch_perc = PlotOptionsSyncState(self, self.viewer, self.layer, 'percentile', 'stretch_perc_value', 'stretch_perc_sync', state_filter=not_profile)
        self.stretch_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_min', 'stretch_min_value', 'stretch_min_sync', state_filter=not_profile)
        self.stretch_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_max', 'stretch_max_value', 'stretch_max_sync', state_filter=not_profile)

        self.bitmap = PlotOptionsSyncState(self, self.viewer, self.layer, 'bitmap_visible', 'bitmap_visible_value', 'bitmap_visible_sync')
        self.color_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'color_mode', 'color_mode_value', 'color_mode_sync')
        self.bitmap_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color', 'bitmap_color_value', 'bitmap_color_sync', state_filter=not_profile)
#        self.bitmap_cmap = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap', 'bitmap_cmap_value', 'bitmap_cmap_sync')
        self.bitmap_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha', 'bitmap_opacity_value', 'bitmap_opacity_sync', state_filter=not_profile)
        self.bitmap_contrast = PlotOptionsSyncState(self, self.viewer, self.layer, 'contrast', 'bitmap_contrast_value', 'bitmap_contrast_sync')
        self.bitmap_bias = PlotOptionsSyncState(self, self.viewer, self.layer, 'bias', 'bitmap_bias_value', 'bitmap_bias_sync')

        self.contour = PlotOptionsSyncState(self, self.viewer, self.layer, 'contour_visible', 'contour_visible_value', 'contour_visible_sync')
        self.contour_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_min', 'contour_min_value', 'contour_min_sync')
        self.contour_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_max', 'contour_max_value', 'contour_max_sync')
        self.contour_nlevels = PlotOptionsSyncState(self, self.viewer, self.layer, 'n_levels', 'contour_nlevels_value', 'contour_nlevels_sync')

        # Axes options:
        self.show_axes = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_axes', 'show_axes_value', 'show_axes_sync', state_filter=not_profile)
        # zoom limits
        # display_units

    def vue_unmix_state(self, name):
        sync_state = getattr(self, name)
        sync_state.unmix_state()

    def vue_set_value(self, data):
        attr_name = data.get('name')
        value = data.get('value')
        setattr(self, attr_name, value)
