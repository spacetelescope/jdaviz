import bqplot
from astropy.visualization import PercentileInterval
from ipywidgets import widget_serialization
from traitlets import Any, Bool

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, DatasetSelectMixin
from jdaviz.utils import bqplot_clear_figure

__all__ = ["Histogram"]


@tray_registry('g-histogram', label="Histogram")
class Histogram(PluginTemplateMixin, ViewerSelectMixin, DatasetSelectMixin):
    template_file = __file__, "histogram.vue"
    plot_available = Bool(False).tag(sync=True)
    histogram = Any('').tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fig = bqplot.Figure(padding_y=0)

    def reset_results(self):
        self.plot_available = False
        self.histogram = ''
        bqplot_clear_figure(self._fig)

    def plot_histogram(self):
        if not self.plugin_opened or not self.viewer_selected or not self.dataset:
            return

        viewer = self.viewer.selected_obj
        data = self.dataset.selected_dc_item
        comp = data.get_component(data.main_components[0])

        # Viewer limits. This takes account of Imviz linking.
        xy_limits = viewer._get_zoom_limits(data).astype(int)
        x_limits = xy_limits[:, 0]
        y_limits = xy_limits[:, 1]
        x_min = x_limits.min()
        x_max = x_limits.max()
        y_min = y_limits.min()
        y_max = y_limits.max()

        # TODO: This only works with Imviz currently. Need to generalize.
        # TODO: If there is performance issues, can try downsample like Compass.
        sub_data = comp.data[y_min:y_max, x_min:x_max].ravel()
        interval = PercentileInterval(95)
        hist_lims = interval.get_limits(sub_data)

        bqplot_clear_figure(self._fig)

        hist_x_sc = bqplot.LinearScale()
        hist_y_sc = bqplot.LinearScale()

        # TODO: Let user change the number of bins?
        hist_plot = bqplot.Hist(sample=sub_data, bins=50, colors="gray",
                                scales={"sample": hist_x_sc, "count": hist_y_sc})
        hist_plot.fig_margin = {'top': 60, 'bottom': 60, 'left': 40, 'right': 10}

        # TODO: Let user change X-axis limits.
        hist_plot.scales['sample'].min = hist_lims[0]
        hist_plot.scales['sample'].max = hist_lims[1]

        self._fig.marks = [hist_plot]
        self._fig.axes = [bqplot.Axis(scale=hist_x_sc, tick_format='0.1e', label='Value'),
                          bqplot.Axis(scale=hist_y_sc, orientation='vertical', label='N')]

        # TODO: Draw viewer cut levels as vertical lines?
        #       If we do this, we need to redraw when Plot Option changes?

        self.histogram = self._fig
        self.bqplot_figs_resize = [self._fig]
        self.plot_available = True

    def vue_plot_histogram(self, event):
        self.plot_histogram()
