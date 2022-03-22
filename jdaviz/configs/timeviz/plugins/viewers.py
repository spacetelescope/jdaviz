from astropy.timeseries import TimeSeries
from glue.core import BaseData
from glue_jupyter.bqplot.profile import BqplotProfileView

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.core.registries import viewer_registry

__all__ = ['TimevizTSView']


@viewer_registry("timeviz-ts-viewer", label="Time Series 1D")
class TimevizTSView(BqplotProfileView, JdavizViewerMixin):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['bqplot:home',
             'jdaviz:boxzoom', 'jdaviz:xrangezoom',
             'bqplot:panzoom', 'bqplot:panzoom_x',
             'bqplot:panzoom_y', 'bqplot:xrange']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['bqplot:home'],
                    ['jdaviz:xrangezoom', 'jdaviz:boxzoom'],
                    ['bqplot:panzoom', 'bqplot:panzoom_x', 'bqplot:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = TimeSeries
    _state_cls = FreezableProfileViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialize_toolbar_nested()

    def data(self, cls=None):
        return [layer_state.layer
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def set_plot_axes(self):
        data = self.data()[0]
        comp = data.get_component('flux')
        self.figure.axes[1].label = comp.units
        self.figure.axes[1].label_offset = "-50"
        self.figure.axes[1].tick_format = '0.4g'
