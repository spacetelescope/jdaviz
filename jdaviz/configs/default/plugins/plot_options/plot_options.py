import logging
import math
import os
import matplotlib
import numpy as np

from astropy.visualization import ManualInterval, ContrastBiasStretch

from echo import delay_callback
from traitlets import Any, Dict, Float, Bool, Int, List, Unicode, observe

from glue.core.subset_group import GroupedSubset
from glue.config import stretches as glue_stretches
from glue.viewers.scatter.state import ScatterViewerState
from glue.viewers.profile.state import ProfileViewerState, ProfileLayerState
from glue.viewers.image.state import ImageSubsetLayerState, ImageViewerState
from glue.viewers.scatter.state import ScatterLayerState as BqplotScatterLayerState
from glue.viewers.image.composite_array import COLOR_CONVERTER
from glue_jupyter.bqplot.image.state import BqplotImageLayerState
from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin, LayerSelect,
                                        PlotOptionsSyncState, Plot,
                                        skip_if_no_updates_since_last_active, with_spinner)
from jdaviz.core.events import ChangeRefDataMessage
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.custom_traitlets import IntHandleEmpty
# by importing from utils, glue_colormaps will include the custom Random colormap
from jdaviz.utils import is_not_wcs_only, cmap_samples, glue_colormaps


from scipy.interpolate import PchipInterpolator

__all__ = ['PlotOptions']

RANDOM_SUBSET_SIZE = 10_000


class SplineStretch:
    """
    A class to represent spline stretches.

    Attributes
    ----------
    k : int
        Degree of the smoothing spline. Default is 3.
    bc_type : str or None
        Boundary condition type. Default is None.
    t : array-like or None
        Array of knot positions. Default is None.
    x : array-like
        The x-coordinates of the data points.
    y : array-like
        The y-coordinates of the data points.
    spline : object
        Interpolating spline.

    Raises
    ------
    ValueError
        If `x` and `y` have different lengths.
    """

    def __init__(self):
        # Default x, y values(0-1) range chosen for a typical initial spline shape.
        # Can be modified if required.
        self._x = np.array([0, 0.1, 0.2, 0.7, 1])
        self._y = np.array([0, 0.05, 0.3, 0.9, 1])
        self.update_knots(self._x, self._y)

    @property
    def knots(self):
        return (self._x, self._y)

    @knots.setter
    def knots(self, value):
        x, y = value
        if len(x) != len(y):
            # Silently return
            return
        self.update_knots(x, y)

    def __call__(self, values, out=None, clip=False):
        # For our uses, we can ignore `out` and `clip`, but those would need
        # to be implemented before contributing this class upstream.
        return self.spline(values)

    def update_knots(self, x, y):
        self._x = x
        self._y = y
        self.spline = PchipInterpolator(self._x, self._y)


# Add the spline stretch to the glue stretch registry if not registered
if "spline" not in glue_stretches:
    glue_stretches.add("spline", SplineStretch, display="Spline")


def _round_step(step):
    # round the step for a float input
    if step <= 0:
        return 1e-6, 6
    decimals = -int(np.log10(abs(step))) + 1 if step != 0 else 6
    if decimals < 0:
        decimals = 0
    return float(np.round(step, decimals)), decimals


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(PluginTemplateMixin, ViewerSelectMixin):
    """
    The Plot Options Plugin gives access to per-viewer and per-layer options and enables
    setting across multiple viewers/layers simultaneously.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
    * ``viewer_multiselect``
    * ``layer`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
    * ``layer_multiselect``
    * :meth:`select_all`
    * ``subset_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      whether a subset should be visible.
    * ``subset_color`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``subset_opacity`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``axes_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Imviz
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
    * ``stretch_hist_nbins`` : number of bins to use in creating the histogram; not exposed
      for Specviz.
    * ``stretch_curve_visible`` : bool
      whether the stretch histogram's colormap "curve" is visible; not exposed for Specviz.
    * ``image_visible`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      whether the image bitmap is visible; not exposed for Specviz.
    * ``image_color_mode`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz
    * ``image_color`` (:class:`~jdaviz.core.template_mixin.PlotOptionsSyncState`):
      not exposed for Specviz.  This only applies when ``image_color_mode`` is "Color".
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
    uses_active_status = Bool(True).tag(sync=True)

    # read-only display units
    display_units = Dict().tag(sync=True)

    viewer_limits = Dict().tag(sync=True)

    layer_multiselect = Bool(False).tag(sync=True)
    layer_items = List().tag(sync=True)
    layer_selected = Any().tag(sync=True)  # Any needed for multiselect

    # profile/line viewer/layer options:
    line_visible_value = Bool().tag(sync=True)
    line_visible_sync = Dict().tag(sync=True)

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

    x_min_value = Float().tag(sync=True)
    x_min_sync = Dict().tag(sync=True)

    x_max_value = Float().tag(sync=True)
    x_max_sync = Dict().tag(sync=True)

    y_min_value = Float().tag(sync=True)
    y_min_sync = Dict().tag(sync=True)

    y_max_value = Float().tag(sync=True)
    y_max_sync = Dict().tag(sync=True)

    x_bound_step = Float(0.1).tag(sync=True)  # dynamic based on maximum value
    y_bound_step = Float(0.1).tag(sync=True)  # dynamic based on maximum value

    zoom_center_x_value = Float().tag(sync=True)
    zoom_center_x_sync = Dict().tag(sync=True)

    zoom_center_y_value = Float().tag(sync=True)
    zoom_center_y_sync = Dict().tag(sync=True)

    zoom_radius_value = Float().tag(sync=True)
    zoom_radius_sync = Dict().tag(sync=True)

    zoom_step = Float(1).tag(sync=True)

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

    stretch_vstep = Float(0.1).tag(sync=True)  # dynamic based on full range from image

    stretch_vmin_value = Float().tag(sync=True)
    stretch_vmin_sync = Dict().tag(sync=True)

    stretch_vmax_value = Float().tag(sync=True)
    stretch_vmax_sync = Dict().tag(sync=True)

    stretch_params_value = Dict().tag(sync=True)
    stretch_params_sync = Dict().tag(sync=True)

    stretch_hist_sync = Dict().tag(sync=True)
    stretch_hist_zoom_limits = Bool().tag(sync=True)
    stretch_hist_nbins = IntHandleEmpty(25).tag(sync=True)
    stretch_histogram_widget = Unicode().tag(sync=True)

    stretch_curve_visible = Bool(True).tag(sync=True)

    subset_visible_value = Bool().tag(sync=True)
    subset_visible_sync = Dict().tag(sync=True)

    subset_color_value = Unicode().tag(sync=True)
    subset_color_sync = Dict().tag(sync=True)

    subset_opacity_value = Float().tag(sync=True)
    subset_opacity_sync = Dict().tag(sync=True)

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

    cmap_samples = Dict(cmap_samples).tag(sync=True)
    swatches_palette = List().tag(sync=True)
    apply_RGB_presets_spinner = Bool(False).tag(sync=True)
    stretch_hist_spinner = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer = LayerSelect(self, 'layer_items', 'layer_selected',
                                 'viewer_selected', 'layer_multiselect')

        self.layer.filters += [is_not_wcs_only]

        self.swatches_palette = [
            ['#FF0000', '#AA0000', '#550000'],
            ['#FFD300', '#AAAA00', '#555500'],
            ['#4CFF00', '#00AA00', '#005500'],
            ['#00FF8E', '#00AAAA', '#005555'],
            ['#0089FF', '#5200FF', '#000055']
        ]

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

        def not_image_viewer(state):
            return not isinstance(state, ImageViewerState)

        def not_image_or_spatial_subset(state):
            return not is_image(state) and not is_spatial_subset(state)

        def is_spatial_subset(state):
            return isinstance(state, ImageSubsetLayerState) and is_not_wcs_only(state.layer)

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
        self.line_visible = PlotOptionsSyncState(self, self.viewer, self.layer, state_attr_for_line_visible,  # noqa
                                                 'line_visible_value', 'line_visible_sync',
                                                 state_filter=supports_line)
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

        # Viewer bounds
        self.x_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'x_min',
                                          'x_min_value', 'x_min_sync',
                                          state_filter=not_image_viewer)
        self.x_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'x_max',
                                          'x_max_value', 'x_max_sync',
                                          state_filter=not_image_viewer)
        self.y_min = PlotOptionsSyncState(self, self.viewer, self.layer, 'y_min',
                                          'y_min_value', 'y_min_sync',
                                          state_filter=not_image_viewer)
        self.y_max = PlotOptionsSyncState(self, self.viewer, self.layer, 'y_max',
                                          'y_max_value', 'y_max_sync',
                                          state_filter=not_image_viewer)
        self.zoom_center_x = PlotOptionsSyncState(self, self.viewer, self.layer, 'zoom_center_x',
                                                  'zoom_center_x_value', 'zoom_center_x_sync')
        self.zoom_center_y = PlotOptionsSyncState(self, self.viewer, self.layer, 'zoom_center_y',
                                                  'zoom_center_y_value', 'zoom_center_y_sync')
        self.zoom_radius = PlotOptionsSyncState(self, self.viewer, self.layer, 'zoom_radius',
                                                'zoom_radius_value', 'zoom_radius_sync')

        # Scatter/marker options:
        # NOTE: marker_visible hides the entire layer (including the line)
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
        # use add_observe to ensure that the glue state syncs with the traitlet choice:
        self.stretch_function.add_observe('stretch_function_value', self._update_stretch_curve)

        self.stretch_preset = PlotOptionsSyncState(self, self.viewer, self.layer, 'percentile',
                                                   'stretch_preset_value', 'stretch_preset_sync',
                                                   state_filter=is_image)
        self.stretch_vmin = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_min',
                                                 'stretch_vmin_value', 'stretch_vmin_sync',
                                                 state_filter=is_image)
        self.stretch_vmax = PlotOptionsSyncState(self, self.viewer, self.layer, 'v_max',
                                                 'stretch_vmax_value', 'stretch_vmax_sync',
                                                 state_filter=is_image)
        self.stretch_params = PlotOptionsSyncState(self, self.viewer, self.layer, 'stretch_parameters',  # noqa
                                                   'stretch_params_value', 'stretch_params_sync',
                                                   state_filter=is_image)

        self.stretch_histogram = Plot(self, name='stretch_hist', viewer_type='histogram',
                                      update_callback=self._update_stretch_histogram)
        # Add the stretch bounds tool to the default Plot viewer.
        self.stretch_histogram.tools_nested.append(["jdaviz:stretch_bounds"])
        self.stretch_histogram._initialize_toolbar(["jdaviz:stretch_bounds"])

        self.stretch_histogram._add_data('histogram', x=[0, 1])

        self.stretch_histogram.add_line('vmin', x=[0, 0], y=[0, 1], ynorm=True, color='#c75d2c')
        self.stretch_histogram.add_line('vmax', x=[0, 0], y=[0, 1], ynorm='vmin', color='#c75d2c')
        self.stretch_histogram.add_line(
            label='stretch_curve',
            x=[], y=[],
            ynorm='vmin',
            color="#007BA1",  # "inactive" blue
            opacities=[0.5],
        )
        self.stretch_histogram.add_scatter(
            label='stretch_knots',
            x=[], y=[],
            ynorm='vmin',
            color="#c75d2c",  # "active" orange (tool enabled by default)
        )
        self.stretch_histogram.add_scatter('colorbar', x=[], y=[], ynorm='vmin', marker='square', stroke_width=33)  # noqa: E501
        self.stretch_histogram.viewer.state.update_bins_on_reset_limits = False
        self.stretch_histogram.viewer.state.x_limits_percentile = 95
        with self.stretch_histogram.figure.hold_sync():
            self.stretch_histogram.figure.axes[0].label = 'pixel value'
            self.stretch_histogram.figure.axes[0].num_ticks = 3
            self.stretch_histogram.figure.axes[0].tick_format = '0.1e'
            self.stretch_histogram.figure.axes[1].label = 'density'
            self.stretch_histogram.figure.axes[1].num_ticks = 2
        self.stretch_histogram_widget = f'IPY_MODEL_{self.stretch_histogram.model_id}'

        self.subset_visible = PlotOptionsSyncState(self, self.viewer, self.layer, 'visible',
                                                   'subset_visible_value', 'subset_visible_sync',
                                                   state_filter=is_spatial_subset)
        self.subset_color = PlotOptionsSyncState(self, self.viewer, self.layer, 'color',
                                                 'subset_color_value', 'subset_color_sync',
                                                 state_filter=is_spatial_subset)
        self.subset_opacity = PlotOptionsSyncState(self, self.viewer, self.layer, 'alpha',
                                                   'subset_opacity_value', 'subset_opacity_sync',
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
        sv = self.spectrum_viewer
        if sv is not None:
            sv.state.add_callback('x_display_unit',
                                  self._on_global_display_unit_changed)
            sv.state.add_callback('y_display_unit',
                                  self._on_global_display_unit_changed)

        self.hub.subscribe(self, ChangeRefDataMessage,
                           handler=self._on_refdata_change)

    @property
    def user_api(self):
        expose = ['multiselect', 'viewer', 'viewer_multiselect', 'layer', 'layer_multiselect',
                  'select_all', 'subset_visible', 'reset_viewer_bounds']
        if self.config == "cubeviz":
            expose += ['uncertainty_visible']
        if self.config != "imviz":
            expose += ['x_min', 'x_max', 'y_min', 'y_max',
                       'axes_visible', 'line_visible', 'line_color', 'line_width', 'line_opacity',
                       'line_as_steps', 'uncertainty_visible']
        if self.config != "specviz":
            expose += ['zoom_center_x', 'zoom_center_y', 'zoom_radius',
                       'subset_color', 'subset_opacity',
                       'stretch_function', 'stretch_preset', 'stretch_vmin', 'stretch_vmax',
                       'stretch_hist_zoom_limits', 'stretch_hist_nbins',
                       'image_visible', 'image_color_mode',
                       'image_color', 'image_colormap', 'image_opacity',
                       'image_contrast', 'image_bias',
                       'contour_visible', 'contour_mode',
                       'contour_min', 'contour_max', 'contour_nlevels', 'contour_custom_levels',
                       'stretch_curve_visible', 'apply_RGB_presets']

        return PluginUserApi(self, expose)

    @property
    def multiselect(self):
        logging.warning(f"DeprecationWarning: multiselect has been replaced by separate viewer_multiselect and layer_multiselect and will be removed in the future.  This currently evaluates viewer_multiselect or layer_multiselect")  # noqa
        return self.viewer_multiselect or self.layer_multiselect

    @multiselect.setter
    def multiselect(self, value):
        logging.warning(f"DeprecationWarning: multiselect has been replaced by separate viewer_multiselect and layer_multiselect and will be removed in the future.  This currently sets viewer_multiselect and layer_multiselect")  # noqa
        self.viewer_multiselect = value
        self.layer_multiselect = value

    def select_all(self, viewers=True, layers=True):
        """
        Enable multiselect mode and select all viewers and/or layers.

        Parameters
        ----------
        viewers : bool
            Whether to set ``viewer_multiselect`` and select all viewers (default: True)

        layers: bool
            Whether to set ``layer_multiselect`` and select all layers (default: True)
        """
        if viewers:
            self.viewer_multiselect = True
            self.viewer.select_all()
        if layers:
            self.layer_multiselect = True
            self.layer.select_all()

    def _on_global_display_unit_changed(self, *args):
        sv = self.spectrum_viewer
        self.display_units['spectral'] = sv.state.x_display_unit
        self.display_units['flux'] = sv.state.y_display_unit
        self.send_state('display_units')

    def _on_refdata_change(self, *args):
        if self.app._align_by.lower() == 'wcs':
            self.display_units['image'] = 'deg'
        else:
            self.display_units['image'] = 'pix'
        self.send_state('display_units')
        self._update_viewer_zoom_steps()

    def vue_unmix_state(self, names):
        if isinstance(names, str):
            names = [names]
        for name in names:
            sync_state = getattr(self, name)
            sync_state.unmix_state()
        if 'stretch_params' in names:
            # there is no way to call send_state to force the update to the layers,
            # so we'll force an update by clearing first
            stretch_params = dict(self.stretch_params_value)
            self.stretch_params_value = {}
            self.stretch_params_value = stretch_params

    def vue_set_value(self, data):
        attr_name = data.get('name')
        value = data.get('value')
        setattr(self, attr_name, value)

    @with_spinner('apply_RGB_presets_spinner')
    def apply_RGB_presets(self):
        """
        Applies preset colors, opacities, and stretch settings to all visible layers
        (in all viewers) when in Color (Monochromatic) mode.
        """

        if (self.image_color_mode_value != "One color per layer" or
                self.image_color_mode_sync['mixed']):
            raise ValueError("RGB presets can only be applied if color mode is Color.")
        # Preselected colors we want to use for 5 or less layers
        preset_colors = [self.swatches_palette[4][1],
                         "#0000FF",
                         "#00FF00",
                         self.swatches_palette[1][0],
                         self.swatches_palette[0][0],
                         ]

        preset_inds = {2: [1, 4], 3: [1, 2, 4], 4: [1, 2, 3, 4]}

        # Switch back to this at the end
        initial_layer = self.layer_selected

        # Determine layers visible in selected viewer(s) - consider mixed to be visible
        visible_layers = [layer['label'] for layer in self.layer.items if not layer['is_subset'] and (layer['visible'] in (True, 'mixed'))]  # noqa

        # Set opacity to something that seems sensible
        n_visible = len(visible_layers)
        default_opacity = 1
        if n_visible > 2:
            default_opacity = 1 / math.log2(n_visible)

        # Sample along a colormap if we have too many layers
        if n_visible > len(preset_colors):
            cmap = matplotlib.colormaps['gist_rainbow'].resampled(n_visible)
            # Have to reverse the order of the cmap to make physical sense with
            # assumed wavelength order of layers.
            preset_colors = [matplotlib.colors.to_hex(cmap(i), keep_alpha=True) for
                             i in range(n_visible - 1, -1, -1)]
        elif n_visible >= 2 and n_visible < len(preset_colors):
            preset_colors = [preset_colors[i] for i in preset_inds[n_visible]]

        for i in range(n_visible):
            self.layer_selected = visible_layers[i]
            self.image_opacity.unmix_state(default_opacity)
            self.image_color.unmix_state(preset_colors[i])
            self.stretch_function.unmix_state("arcsinh")
            self.stretch_preset.unmix_state(99)

        self.layer_selected = initial_layer

    def vue_apply_RGB_presets(self, data):
        self.apply_RGB_presets()

    @observe('viewer_selected',
             'x_min_value', 'x_max_value',
             'y_min_value', 'y_max_value')
    def _update_viewer_bound_steps(self, msg={}):
        if not hasattr(self, 'viewer'):  # pragma: no cover
            # plugin hasn't been fully initialized yet
            return

        if not self.viewer.selected or not self.x_min_sync['in_subscribed_states']:
            # nothing selected yet
            return

        for ax in ('x', 'y'):
            ax_min = getattr(self, f'{ax}_min_value')
            ax_max = getattr(self, f'{ax}_max_value')
            bound_step, decimals = _round_step((ax_max - ax_min) / 100.)
            decimals = -int(np.log10(abs(bound_step))) + 1 if bound_step != 0 else 6
            setattr(self, f'{ax}_bound_step', bound_step)
            setattr(self, f'{ax}_min_value', np.round(ax_min, decimals=decimals))
            setattr(self, f'{ax}_max_value', np.round(ax_max, decimals=decimals))

    @observe('viewer_selected',
             'zoom_center_x_value', 'zoom_center_y_value',
             'zoom_radius_value')
    def _update_viewer_zoom_steps(self, msg={}):
        if not hasattr(self, 'viewer'):  # pragma: no cover
            # plugin hasn't been fully initialized yet
            return

        if not self.viewer.selected or not self.zoom_radius_sync['in_subscribed_states']:
            # nothing selected yet
            return

        # in the case of multiple viewers, calculate based on the first
        # alternatively, we could find the most extreme by looping over all selected viewers
        viewers = self.viewer.selected_obj if self.viewer_multiselect else [self.viewer.selected_obj]  # noqa
        for viewer in viewers:
            if hasattr(viewer.state, '_get_reset_limits'):
                break
        else:
            # no image viewer
            return
        x_min, x_max, y_min, y_max = viewer.state._get_reset_limits(return_as_world=True)
        self.zoom_step, _ = _round_step(max(x_max-x_min, y_max-y_min) / 100.)

    def vue_reset_viewer_bounds(self, _):
        self.reset_viewer_bounds()

    def reset_viewer_bounds(self):
        # This button is currently only exposed if only the spectrum viewer is selected
        viewers = [self.viewer.selected_obj] if not self.viewer_multiselect else self.viewer.selected_obj # noqa
        for viewer in viewers:
            viewer.toolbar.tools['jdaviz:homezoom'].activate()

    @observe('stretch_function_sync', 'stretch_params_sync',
             'stretch_vmin_sync', 'stretch_vmax_sync',
             'image_color_mode_sync', 'image_color_sync', 'image_colormap_sync')
    def _update_stretch_hist_sync(self, msg={}):
        # the histogram should show as mixed if ANY of the input parameters are mixed
        # these should match in the @observe above, all_syncs here, as well as the strings
        # passed to unmix_state in the <glue-state-sync-wrapper> in plot_options.vue
        all_syncs = [self.stretch_function_sync, self.stretch_params_sync,
                     self.stretch_vmin_sync, self.stretch_vmax_sync,
                     self.image_color_mode_sync, self.image_color_sync, self.image_colormap_sync]
        self.stretch_hist_sync = {'in_subscribed_states': bool(np.any([sync.get('in_subscribed_states', False) for sync in all_syncs])),  # noqa
                                  'mixed': bool(np.any([sync.get('mixed', False) for sync in all_syncs]))}  # noqa

    @observe('is_active', 'layer_selected', 'viewer_selected',
             'stretch_hist_zoom_limits')
    @skip_if_no_updates_since_last_active()
    def _request_update_stretch_histogram(self, msg={}):
        if not hasattr(self, 'viewer'):  # pragma: no cover
            # plugin hasn't been fully initialized yet
            return

        # NOTE: this method is separate from _update_stretch_histogram so that
        # _update_stretch_histogram can be called manually (or from the
        # update_callback on the Plot object itself) without going through
        # the skip_if_no_updates_since_last_active check (and can therefore
        # be executed even if the plugin is not active)
        self._update_stretch_histogram(msg)

    def _zoom_limits_update_stretch_histogram(self, msg={}):
        if not self.stretch_hist_zoom_limits:
            # there isn't anything to update, let's not waste resources
            return
        self._update_stretch_histogram()

    @with_spinner('stretch_hist_spinner')
    def _update_stretch_histogram(self, msg={}):
        if not self.stretch_function_sync.get('in_subscribed_states'):  # pragma: no cover
            # no (image) viewer with stretch function options
            return

        if not self.viewer.selected or not self.layer.selected:  # pragma: no cover
            # nothing to plot, will be hidden in UI
            return

        if self.layer_multiselect and len(self.layer.selected) > 1:
            # currently only support single-layer, if multiple layers are selected, the plot
            # will be hidden in the UI
            return

        if not self._viewer_is_image_viewer():
            # don't update histogram if selected viewer is not an image viewer:
            return

        viewer = self.viewer.selected_obj[0] if self.viewer_multiselect else self.viewer.selected_obj  # noqa

        # manage viewer zoom limit callbacks
        if ((isinstance(msg, dict) and msg.get('name') == 'viewer_selected')
                or not self.stretch_hist_zoom_limits):
            vs = viewer.state
            for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
                vs.add_callback(attr, self._zoom_limits_update_stretch_histogram)
        if isinstance(msg, dict) and msg.get('name') == 'viewer_selected':
            viewer_label_old = msg.get('old')
            if isinstance(viewer_label_old, list):
                viewer_label_old = viewer_label_old[0]
            # If the previously selected viewer was deleted, we don't need to do this.
            if viewer_label_old in self.app._viewer_store:
                vs_old = self.app.get_viewer(viewer_label_old).state
                for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
                    vs_old.remove_callback(attr, self._zoom_limits_update_stretch_histogram)

        if not len(self.layer.selected_obj):
            # skip further updates if no data are available:
            return
        if isinstance(self.layer.selected_obj[0], list):
            if not len(self.layer.selected_obj[0]):
                return
            # multiselect case (but we won't check multiselect since the selection can lag behind)
            layer = self.layer.selected_obj[0][0]
        else:
            layer = self.layer.selected_obj[0]
        data = layer.layer

        if isinstance(data, GroupedSubset):
            # don't update histogram for subsets:
            return

        comp = data.get_component(layer.state.attribute)

        # TODO: further optimization could be done by caching sub_data
        if self.stretch_hist_zoom_limits and (not self.layer_multiselect or len(self.layer_selected) == 1):  # noqa
            if hasattr(viewer, '_get_zoom_limits'):
                # Viewer limits. This takes account of Imviz linking.
                xy_limits = viewer._get_zoom_limits(data).astype(int)
                x_limits = xy_limits[:, 0]
                y_limits = xy_limits[:, 1]
                x_min = max(x_limits.min(), 0)
                x_max = x_limits.max()
                y_min = max(y_limits.min(), 0)
                y_max = y_limits.max()

                sub_data = comp.data[y_min:y_max, x_min:x_max]

            else:
                # spectrum-2d-viewer, for example.  We'll assume the viewer
                # limits correspond to the fixed data components from glue
                # and filter directly.
                x_data = data.get_component(data.components[1]).data
                y_data = data.get_component(data.components[0]).data

                inverted_x = getattr(viewer, 'inverted_x_axis', False)
                x_min = viewer.state.x_min if not inverted_x else viewer.state.x_max
                x_max = viewer.state.x_max if not inverted_x else viewer.state.x_min
                inds = np.where((x_data >= x_min) &
                                (x_data <= x_max) &
                                (y_data >= viewer.state.y_min) &
                                (y_data <= viewer.state.y_max))

                sub_data = comp.data[inds]

        else:
            # include all data, regardless of zoom limits
            sub_data = comp.data

        self.stretch_histogram.viewer.state.random_subset = RANDOM_SUBSET_SIZE
        self.stretch_histogram._update_data('histogram', x=sub_data)

        if len(sub_data) > 0:

            # Use glue to compute the statistics since this allows us to use
            # a random subset of the data to compute the histogram.
            # The 2.5 and 97.5 hardcoded here is equivalent to
            # PercentileInterval(95).get_limits(sub_data)
            glue_data = self.stretch_histogram.app.data_collection['histogram']
            hist_lims = (
                glue_data.compute_statistic('percentile', glue_data.id['x'],
                                            percentile=2.5, random_subset=RANDOM_SUBSET_SIZE),
                glue_data.compute_statistic('percentile', glue_data.id['x'],
                                            percentile=97.5, random_subset=RANDOM_SUBSET_SIZE)
            )

            # set the stepsize for vmin/vmax to be approximately 1% of the range of the
            # histogram (within the percentile interval), rounded to 1-2 significant digits
            # to avoid random step sizes.  This logic is somewhat arbitrary and can be safely
            # modified or eventually exposed to the user if that would be useful.
            stretch_vstep = (hist_lims[1] - hist_lims[0]) / 100.
            self.stretch_vstep = _round_step(stretch_vstep)[0]

            with delay_callback(self.stretch_histogram.viewer.state, 'hist_x_min', 'hist_x_max'):
                self.stretch_histogram.viewer.state.hist_x_min = hist_lims[0]
                self.stretch_histogram.viewer.state.hist_x_max = hist_lims[1]

        self.stretch_histogram.figure.title = f"{len(sub_data)} pixels"

        # update the n_bins since this may be a new layer
        self._histogram_nbins_changed()
        # update the curve/colorbar
        self._update_stretch_curve(msg)

    @observe('image_color_mode_value', 'image_color_value', 'image_colormap_value',
             'image_contrast_value', 'image_bias_value',
             'stretch_hist_nbins',
             'stretch_curve_visible',
             'stretch_function_value', 'stretch_vmin_value', 'stretch_vmax_value',
             'stretch_params_value', 'stretch_preset_value',
             'layer_multiselect'
             )
    @skip_if_no_updates_since_last_active()
    def _update_stretch_curve(self, msg=None):
        if not self._viewer_is_image_viewer() or not hasattr(self, 'stretch_histogram'):
            # don't update histogram if selected viewer is not an image viewer,
            # or the stretch histogram hasn't been initialized:
            return

        if self.layer_multiselect and len(self.layer.selected) > 1:
            # currently only support single-layer, if multiple layers are selected, the plot
            # will be hidden in the UI
            return

        # could be multi or single-viewer and/or multi-layer with a single entry,
        # either way, we act on the first entry
        layer = self.layer.selected_obj[0]
        while isinstance(layer, list):
            if not len(layer):
                return
            layer = layer[0]

        if isinstance(layer.layer, GroupedSubset):
            # don't update histogram for subsets, will be hidden in UI
            return

        # create the new/updated stretch curve following the colormapping
        # procedure in glue's CompositeArray:
        interval = ManualInterval(self.stretch_vmin_value, self.stretch_vmax_value)
        contrast_bias = ContrastBiasStretch(self.image_contrast_value, self.image_bias_value)
        stretch = layer.state.stretch_object
        layer_cmap = layer.state.cmap

        # show the colorbar
        color_mode = self.image_color_mode_value

        # NOTE: Index 0 in marks is assumed to be the bin centers.
        x = self.stretch_histogram.figure.marks[0].x
        y = np.ones_like(x)

        # Copied from the __call__ internals of glue/viewers/image/composite_array.py
        data = interval(x)
        data = contrast_bias(data, out=data)
        data = stretch(data, out=data)

        if color_mode == 'Colormaps':
            cmap = glue_colormaps[self.image_colormap.text]
            if hasattr(cmap, "get_bad"):
                bad_color = cmap.get_bad().tolist()[:3]
                layer_cmap = cmap.with_extremes(bad=bad_color + [self.image_opacity_value])
            else:
                layer_cmap = cmap

            # Compute colormapped image
            plane = layer_cmap(data)

        else:  # Color (Monochromatic)
            if self.image_color_value is None:
                # do not crash if image_color_value is not yet assigned,
                # _update_stretch_curve observes image_color_value so will get called again
                return False
            # Get color
            color = COLOR_CONVERTER.to_rgba_array(self.image_color_value)[0]
            plane = data[:, np.newaxis] * color
            plane[:, 3] = 1

        plane = np.clip(plane, 0, 1, out=plane)
        ipycolors = [matplotlib.colors.rgb2hex(p, keep_alpha=False) for p in plane]

        colorbar_mark = self.stretch_histogram.marks['colorbar']
        colorbar_mark.x = x
        colorbar_mark.y = y
        colorbar_mark.colors = ipycolors

        # show "knot" locations if the stretch_function is a spline
        if isinstance(stretch, SplineStretch) and self.stretch_curve_visible:
            knot_mark = self.stretch_histogram.marks['stretch_knots']
            knot_mark.x = (self.stretch_vmin_value +
                           np.asarray(stretch._x) * (self.stretch_vmax_value - self.stretch_vmin_value))  # noqa
            # scale to 0.9 so always falls below colorbar (same as for stretch_curve)
            knot_mark.y = 0.9 * np.asarray(stretch._y)
        else:
            self.stretch_histogram.clear_marks('stretch_knots')

        if self.stretch_curve_visible:
            # create a photoshop style "curve" for the stretch function
            curve_x = np.linspace(self.stretch_vmin_value, self.stretch_vmax_value, 50)
            curve_y = interval(curve_x)
            curve_y = contrast_bias(curve_y)
            curve_y = stretch(curve_y)

            curve_mark = self.stretch_histogram.marks['stretch_curve']
            curve_mark.x = curve_x
            curve_mark.y = 0.9 * curve_y
        else:
            self.stretch_histogram.clear_marks('stretch_curve')

        self.stretch_histogram._refresh_marks()

    @observe('stretch_vmin_value')
    def _stretch_vmin_changed(self, msg=None):
        self.stretch_histogram.marks['vmin'].x = [self.stretch_vmin_value, self.stretch_vmin_value]

    @observe('stretch_vmax_value')
    def _stretch_vmax_changed(self, msg=None):
        self.stretch_histogram.marks['vmax'].x = [self.stretch_vmax_value, self.stretch_vmax_value]

    @observe("stretch_hist_nbins")
    def _histogram_nbins_changed(self, msg={}):
        if self.stretch_histogram is None:
            return
        if self.stretch_hist_nbins == '' or self.stretch_hist_nbins < 1:
            return
        self.stretch_histogram.viewer.state.hist_n_bin = self.stretch_hist_nbins
        # for some reason, this resets the internal marks, so we need to ensure the manual
        # marks are still plotted
        self.stretch_histogram._refresh_marks()

    def set_histogram_limits(self, x_min=None, x_max=None, y_min=None, y_max=None):
        # NOTE: leaving this out of user API until API is finalized with interactive setting
        self.stretch_histogram.set_limits(x_min=x_min, x_max=x_max,
                                          y_min=y_min, y_max=y_max)

    def _viewer_is_image_viewer(self):
        # Import here to prevent circular import (and not at the top of the method so the import
        # check is avoided, whenever possible).
        from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
        from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView
        from jdaviz.configs.mosviz.plugins.viewers import MosvizImageView, MosvizProfile2DView
        from jdaviz.configs.rampviz.plugins.viewers import RampvizImageView

        def _is_image_viewer(viewer):
            return isinstance(viewer, (ImvizImageView, CubevizImageView,
                                       MosvizImageView, MosvizProfile2DView,
                                       RampvizImageView))

        viewers = self.viewer.selected_obj
        if not isinstance(viewers, list):
            viewers = [viewers]

        return np.all([_is_image_viewer(viewer) for viewer in viewers])

    def image_segmentation_map_presets(self, *args, **kwargs):
        # if 'Random' colormap is used for visualizing image segmentation,
        # ensure the stretch limits are the min and max, the stretch function
        # is linear, the contrast is 1.0, and the bias is 0.5. This ensures
        # that all label colors are unique:
        if self.image_colormap_value != 'Random':
            return

        self.stretch_preset.value = 100
        self.stretch_function.value = 'linear'
        self.image_contrast_value = 1
        self.image_bias_value = 0.5

    def vue_image_segmentation_map_presets(self, *args, **kwargs):
        self.image_segmentation_map_presets(*args, **kwargs)
