import numpy as np
from astropy.nddata import NDDataArray
from glue.core import BaseData
from glue.core.subset import Subset
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin, JdavizProfileView
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceSelection, WithSliceIndicator
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState

__all__ = ['RampvizProfileView', 'RampvizImageView']


@viewer_registry("rampviz-profile-viewer", label="Profile 1D (Rampviz)")
class RampvizProfileView(JdavizProfileView, WithSliceIndicator):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['jdaviz:selectslice'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _default_profile_subset_type = 'temporal'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_tool_priority', ['jdaviz:selectslice'])
        super().__init__(*args, **kwargs)

    def _initialize_x_axis(self):
        if len(self.state.x_att_helper.choices):
            self.state.x_att = self.state.x_att_helper.choices[-1]
            self.set_plot_axes()
            self.reset_limits()

    def reset_limits(self):
        # override to reset to the global y limits including marks:
        global_y_min = np.inf
        global_y_max = -np.inf
        for mark in self.figure.marks:
            if len(mark.y) and mark.visible:
                global_y_min = min(global_y_min, np.nanmin(mark.y))
                global_y_max = max(global_y_max, np.nanmax(mark.y))

        for layer in self.state.layers:
            if not isinstance(layer.layer, Subset) and layer.visible:
                component = layer.layer.main_components[0]
                layer_y_min = layer.layer.get_component(component).data.min()
                layer_y_max = layer.layer.get_component(component).data.max()

                global_y_min = min(global_y_min, layer_y_min)
                global_y_max = max(global_y_max, layer_y_max)

        y_buffer = 0.1

        y_min = (1 - y_buffer) * global_y_min
        y_max = (1 + y_buffer) * global_y_max
        if y_min != self.state.y_min or y_max != self.state.y_max:
            self.set_limits(y_min=y_min, y_max=y_max)

    def set_plot_axes(self):

        with self.figure.hold_sync():
            self.figure.axes[0].label = "Group"
            self.figure.axes[1].label = self.state.y_display_unit

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


@viewer_registry("rampviz-image-viewer", label="Image 2D (Rampviz)")
class RampvizImageView(JdavizViewerMixin, WithSliceSelection, BqplotImageView):
    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:pixelboxzoommatch', 'jdaviz:boxzoom'],
                    ['jdaviz:pixelpanzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                     'bqplot:circannulus'],
                    ['jdaviz:rampperpixel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide reference from state back to viewer to use for zoom syncing
        self.state._set_viewer(self)

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        # Hide axes by default
        self.state.show_axes = False

    @property
    def _default_group_viewer_reference_name(self):
        return self.jdaviz_helper._default_group_viewer_reference_name

    @property
    def _default_diff_viewer_reference_name(self):
        return self.jdaviz_helper._default_diff_viewer_reference_name

    @property
    def _default_integration_viewer_reference_name(self):
        return self.jdaviz_helper._default_integration_viewer_reference_name

    def _initial_x_axis(self, *args):
        # Make sure that the x_att is correct on data load
        ref_data = self.state.reference_data

        if ref_data:
            if "Pixel Axis 0 [z]" in [comp.label for comp in ref_data.components]:
                self.state.x_att = ref_data.id["Pixel Axis 0 [z]"]
            else:
                self.state.x_att = ref_data.id["Pixel Axis 0 [y]"]

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
