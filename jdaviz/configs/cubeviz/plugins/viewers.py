from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicator
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView

__all__ = ['CubevizImageView', 'CubevizProfileView']


@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(BqplotImageView, JdavizViewerMixin):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['bqplot:home', 'jdaviz:boxzoom',
             'bqplot:panzoom', 'bqplot:rectangle',
             'bqplot:circle']

    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['bqplot:home'],
                    ['jdaviz:boxzoom', 'bqplot:panzoom'],
                    ['bqplot:circle', 'bqplot:rectangle'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialize_toolbar_nested()

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


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(SpecvizProfileView):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['bqplot:home',
             'jdaviz:boxzoom', 'jdaviz:xrangezoom',
             'bqplot:panzoom', 'bqplot:panzoom_x',
             'bqplot:panzoom_y', 'bqplot:xrange',
             'jdaviz:selectslice', 'jdaviz:selectline']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['bqplot:home'],
                    ['jdaviz:xrangezoom', 'jdaviz:boxzoom'],
                    ['bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        # NOTE: super will initialize nested toolbar with
        # default_tool_priority=['jdaviz:selectslice']
        super().__init__(*args, **kwargs)

    @property
    def slice_indicator(self):
        for mark in self.figure.marks:
            if isinstance(mark, SliceIndicator):
                return mark

        # SliceIndicator does not yet exist
        slice_indicator = SliceIndicator(self)
        self.figure.marks = self.figure.marks + [slice_indicator]
        return slice_indicator

    def _update_slice_indicator(self, slice):
        self.slice_indicator.slice = slice
