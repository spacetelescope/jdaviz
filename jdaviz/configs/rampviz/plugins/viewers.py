from astropy.nddata import NDDataArray
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin, JdavizProfileView
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceSelection, WithSliceIndicator
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState, FreezableProfileViewerState

__all__ = ['RampvizProfileView', 'RampvizImageView']


@viewer_registry("rampviz-profile-viewer", label="Profile 1D (Rampviz)")
class RampvizProfileView(JdavizProfileView, WithSliceIndicator):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _state_cls = FreezableProfileViewerState
    _default_profile_subset_type = 'temporal'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_tool_priority', ['jdaviz:selectslice'])
        super().__init__(*args, **kwargs)


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
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide reference from state back to viewer to use for zoom syncing
        self.state._viewer = self

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
        if ref_data and ref_data.ndim == 3:
            x_att = "Pixel Axis 0 [z]"
            self.state.x_att = ref_data.id[x_att]

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
