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

    default_class = None

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


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Specviz)")
class CubevizProfileView(SpecvizProfileView):
    @property
    def slice_indicator(self):
        for mark in self.figure.marks:
            if isinstance(mark, SliceIndicator):
                return mark

        # SliceIndicator does not yet exist
        # TODO: can we do this better, do we need to convert to displayed units??
        x_all = self.data()[0].spectral_axis.value
        slice_indicator = SliceIndicator(x_all, self.scales)
        self.figure.marks = self.figure.marks + [slice_indicator]
        return slice_indicator

    def _update_slice_indicator(self, slice):
        self.slice_indicator.update_slice(slice)
