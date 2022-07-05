import os

from traitlets import Any, Dict, Float, Bool, Int, List, Unicode

from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.viewers.image.state import ImageSubsetLayerState
from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (TemplateMixin, ViewerSelect, LayerSelect,
                                        PlotOptionsSyncState)
from jdaviz.core.tools import ICON_DIR

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

    # spectrum viewer/layer options:
    layer_visible_value = Bool().tag(sync=True)
    layer_visible_sync = Dict().tag(sync=True)

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

    subset_visible_value = Bool().tag(sync=True)
    subset_visible_sync = Dict().tag(sync=True)

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

    show_axes_value = Bool().tag(sync=True)
    show_axes_sync = Dict().tag(sync=True)

    icon_radialtocheck = Unicode(read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml')).tag(sync=True)  # noqa
    icon_checktoradial = Unicode(read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'multiselect')
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected', 'viewer_selected', 'multiselect')  # noqa

        def not_profile(state):
            return not isinstance(state, (ProfileViewerState, ProfileLayerState))

        def is_profile(state):
            return isinstance(state, (ProfileViewerState, ProfileLayerState))

        def is_spatial_subset(state):
            return isinstance(state, ImageSubsetLayerState)

        def is_not_subset(state):
            return not isinstance(state, ImageSubsetLayerState)

        # Spectrum viewer/layer options:
        self.layer_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                  'layer_visible_value', 'layer_visible_sync',
                                                  state_filter=is_not_subset)
        self.collapse_function = PlotOptionsSyncState(self, self.viewer, self.layer, 'function',
                                                      'collapse_func_value', 'collapse_func_sync')
        self.line_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                               'line_color_value', 'line_color_sync',
                                               state_filter=is_profile)
        self.line_width = PlotOptionsSyncState(self, self.viewer, self.layer, 'linewidth',
                                               'line_width_value', 'line_width_sync')
        self.line_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                 'line_opacity_value', 'line_opacity_sync',
                                                 state_filter=is_profile)
        self.uncertainty = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_uncertainty',
                                                'uncertainty_value', 'uncertainty_sync')

        # Image viewer/layer options:
        self.stretch = PlotOptionsSyncState(self, self.viewer, self.layer, 'stretch',
                                            'stretch_value', 'stretch_sync',
                                            state_filter=not_profile)
        self.stretch_perc = PlotOptionsSyncState(self, self.viewer, self.layer, 'percentile',
                                                 'stretch_perc_value', 'stretch_perc_sync',
                                                 state_filter=not_profile)
        self.stretch_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_min',
                                                'stretch_min_value', 'stretch_min_sync',
                                                state_filter=not_profile)
        self.stretch_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_max',
                                                'stretch_max_value', 'stretch_max_sync',
                                                state_filter=not_profile)

        self.subset_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                   'subset_visible_value', 'subset_visible_sync',
                                                   state_filter=is_spatial_subset)
        self.bitmap_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'bitmap_visible',
                                                   'bitmap_visible_value', 'bitmap_visible_sync',
                                                   state_filter=not_profile)
        self.color_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'color_mode',
                                               'color_mode_value', 'color_mode_sync')
        self.bitmap_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                                 'bitmap_color_value', 'bitmap_color_sync',
                                                 state_filter=not_profile)
        self.bitmap_cmap = PlotOptionsSyncState(self, self.viewer, self.layer, 'cmap',
                                                'bitmap_cmap_value', 'bitmap_cmap_sync')
        self.bitmap_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                   'bitmap_opacity_value', 'bitmap_opacity_sync',
                                                   state_filter=not_profile)
        self.bitmap_contrast = PlotOptionsSyncState(self, self.viewer, self.layer, 'contrast',
                                                    'bitmap_contrast_value', 'bitmap_contrast_sync')
        self.bitmap_bias = PlotOptionsSyncState(self, self.viewer, self.layer, 'bias',
                                                'bitmap_bias_value', 'bitmap_bias_sync')

        self.contour_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'contour_visible',  # noqa
                                                    'contour_visible_value', 'contour_visible_sync')
        self.contour_mode = PlotOptionsSyncState(self, self.viewer, self.layer, 'level_mode',
                                                 'contour_mode_value', 'contour_mode_sync')
        self.contour_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_min',
                                                'contour_min_value', 'contour_min_sync')
        self.contour_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'c_max',
                                                'contour_max_value', 'contour_max_sync')
        self.contour_nlevels = PlotOptionsSyncState(self, self.viewer, self.layer, 'n_levels',
                                                    'contour_nlevels_value', 'contour_nlevels_sync')
        self.contour_custom_levels = PlotOptionsSyncState(self, self.viewer, self.layer, 'levels',
                                                          'contour_custom_levels_value', 'contour_custom_levels_sync')  # noqa

        # Axes options:
        # show_axes hidden for imviz in plot_options.vue
        self.show_axes = PlotOptionsSyncState(self, self.viewer, self.layer, 'show_axes',
                                              'show_axes_value', 'show_axes_sync',
                                              state_filter=not_profile)
        # zoom limits
        # display_units

    def vue_unmix_state(self, name):
        sync_state = getattr(self, name)
        sync_state.unmix_state()

    def vue_set_value(self, data):
        attr_name = data.get('name')
        value = data.get('value')
        setattr(self, attr_name, value)
