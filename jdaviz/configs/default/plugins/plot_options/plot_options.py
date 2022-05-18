from traitlets import Any, Dict, Float, Bool, Int, List, Unicode, observe
from ipywidgets.widgets import widget_serialization

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

    # Whether the currently selected viewer has the ability to toggle uncertainty
    has_show_uncertainty = Bool(False).tag(sync=True)
    # Toggle for showing uncertainty in the currently selected viewer
    show_uncertainty = Bool(False).tag(sync=True)

    # shared viewer options:


    # spectrum viewer/layer options:
    collapse_func_value = Unicode().tag(sync=True)
    collapse_func_sync = Dict().tag(sync=True)
    ## color
    linewidth_value = Int().tag(sync=True)
    linewidth_sync = Dict().tag(sync=True)
    ## show_uncertainty

    # image viewer/layer options
    stretch_value = Unicode().tag(sync=True)
    stretch_sync = Dict().tag(sync=True)

    stretch_perc_value = Any().tag(sync=True)  # glue will pass either a float or string
    stretch_perc_sync = Dict().tag(sync=True)

    stretch_min_value = Float().tag(sync=True)
    stretch_min_sync = Dict().tag(sync=True)

    stretch_max_value = Float().tag(sync=True)
    stretch_max_sync = Dict().tag(sync=True)

    color_mode_value = Unicode().tag(sync=True)
    color_mode_sync = Dict().tag(sync=True)

    bitmap_visible_value = Bool().tag(sync=True)
    bitmap_visible_sync = Dict().tag(sync=True)

    contour_visible_value = Bool().tag(sync=True)
    contour_visible_sync = Dict().tag(sync=True)

    show_axes_value = Bool().tag(sync=True)
    show_axes_sync = Dict().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'multiselect')
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected', 'viewer_selected', 'multiselect')

        # Shared viewer options:
        # zoom_limits
        # axes_labels
        # display_units

        # Spectrum viewer/layer options:
        self.collapse_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'function', 'collapse_func_value', 'collapse_func_sync')
#        self.color = PlotOptionsColorState(self, 'color', 'color_mixed')
        self.linewidth = PlotOptionsSyncState(self, self.viewer, self.layer, 'linewidth', 'linewidth_value', 'linewidth_sync')
#        self.show_uncertainty = PlotOptionsBoolState(self, self.viewer, self.layer, 'show_uncertainty_value', 'show_uncertainty_sync')  # NOTE: not upstream!

        # Image viewer/layer options:
        self.stretch = PlotOptionsSyncState(self, self.viewer, self.layer, 'stretch', 'stretch_value', 'stretch_sync')
        self.stretch_perc = PlotOptionsSyncState(self, self.viewer, self.layer, 'percentile', 'stretch_perc_value', 'stretch_perc_sync')
        self.stretch_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_min', 'stretch_min_value', 'stretch_min_sync')
        self.stretch_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_max', 'stretch_max_value', 'stretch_max_sync')

        self.color_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'color_mode', 'color_mode_value', 'color_mode_sync')
#        # color IF color_mode is color-per-layer, or as part of bitmap?
#        self.stretch = PlotOptionsStretchState(self, 'stretch_items', 'stretch_items_selected', 'stretch_percentiale', 'stretch_min', 'stretch_max', 'stretch_mixed')
#        self.contour = PlotOptionsContourState(self, 'contour_enabled', ...)
        self.bitmap = PlotOptionsSyncState(self, self.viewer, self.layer, 'bitmap_visible', 'bitmap_visible_value', 'bitmap_visible_sync')
        self.contour = PlotOptionsSyncState(self, self.viewer, self.layer, 'contour_visible', 'contour_visible_value', 'contour_visible_sync')
        self.show_axes = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_axes', 'show_axes_value', 'show_axes_sync')

    def vue_unmix_state(self, name):
        sync_state = getattr(self, name)
        sync_state.unmix_state()
