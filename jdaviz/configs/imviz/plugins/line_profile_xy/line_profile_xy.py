import bqplot
from ipywidgets import widget_serialization
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.utils import bqplot_clear_figure

__all__ = ['LineProfileXY']


@tray_registry('imviz-line-profile-xy', label="Imviz Line Profiles (XY)")
class LineProfileXY(PluginTemplateMixin):
    template_file = __file__, "line_profile_xy.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    selected_x = Any('').tag(sync=True)
    selected_y = Any('').tag(sync=True)
    line_plot_across_x = Any('').tag(sync=True, **widget_serialization)
    line_plot_across_y = Any('').tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_viewer = f'{self.app.config}-0'

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)

        self._figs = [bqplot.Figure(), bqplot.Figure()]
        self._on_viewers_changed()  # Populate it on start-up

    def _on_viewers_changed(self, msg=None):
        self.viewer_items = self.app.get_viewer_ids()

        # Selected viewer was removed but Imviz always has a default viewer to fall back on.
        if self.selected_viewer not in self.viewer_items:
            self.selected_viewer = self._default_viewer

    def reset_results(self):
        self.plot_available = False
        self.line_plot_across_x = ''
        self.line_plot_across_y = ''
        for fig in self._figs:
            bqplot_clear_figure(fig)

    # This is also triggered from viewer code.
    @observe("selected_viewer")
    def vue_draw_plot(self, *args, **kwargs):
        """Draw line profile plots for given Data across given X and Y indices (0-indexed)."""
        if not self.selected_x or not self.selected_y or not self.plugin_opened:
            return

        viewer = self.app.get_viewer_by_id(self.selected_viewer)
        i = get_top_layer_index(viewer)
        data = viewer.state.layers[i].layer

        # Can be str if passed in from Vue.js
        x = int(round(float(self.selected_x)))
        y = int(round(float(self.selected_y)))

        nx = data.shape[1]
        ny = data.shape[0]
        if x < 0 or y < 0 or x >= nx or y >= ny:
            self.reset_results()
            return

        xy_limits = viewer._get_zoom_limits(data)
        x_limits = xy_limits[:, 0]
        y_limits = xy_limits[:, 1]
        x_min = x_limits.min()
        x_max = x_limits.max()
        y_min = y_limits.min()
        y_max = y_limits.max()

        comp = data.get_component(data.main_components[0])
        if comp.units:
            y_label = comp.units
        else:
            y_label = 'Value'

        # Clear bqplot figure (copied from bqplot/pyplot.py)
        for fig in self._figs:
            fig.marks = []
            fig.axes = []
            setattr(fig, 'axis_registry', {})

        fig_x = self._figs[0]
        bqplot_clear_figure(fig_x)

        fig_y = self._figs[1]
        bqplot_clear_figure(fig_y)

        fig_x.title = f'X={x}'
        fig_x.title_style = {'font-size': '12px'}
        fig_x.fig_margin = {'top': 60, 'bottom': 60, 'left': 40, 'right': 10}
        line_x_x_sc = bqplot.LinearScale()
        line_x_y_sc = bqplot.LinearScale()
        line_x = bqplot.Lines(x=range(comp.data.shape[0]), y=comp.data[:, x],
                              scales={'x': line_x_x_sc, 'y': line_x_y_sc}, colors='gray')
        fig_x.marks = [line_x]
        fig_x.axes = [bqplot.Axis(scale=line_x_x_sc, label='Y (pix)'),
                      bqplot.Axis(scale=line_x_y_sc, orientation='vertical', label=y_label)]
        line_x.scales['x'].min = y_min
        line_x.scales['x'].max = y_max
        y_min = max(int(y_min), 0)
        y_max = min(int(y_max), ny)
        zoomed_data_x = comp.data[y_min:y_max, x]
        if zoomed_data_x.size > 0:
            line_x.scales['y'].min = zoomed_data_x.min() * 0.95
            line_x.scales['y'].max = zoomed_data_x.max() * 1.05

        fig_y.title = f'Y={y}'
        fig_y.title_style = {'font-size': '12px'}
        fig_y.fig_margin = {'top': 60, 'bottom': 60, 'left': 40, 'right': 10}
        line_y_x_sc = bqplot.LinearScale()
        line_y_y_sc = bqplot.LinearScale()
        line_y = bqplot.Lines(x=range(comp.data.shape[1]), y=comp.data[y, :],
                              scales={'x': line_y_x_sc, 'y': line_y_y_sc}, colors='gray')
        fig_y.marks = [line_y]
        fig_y.axes = [bqplot.Axis(scale=line_y_x_sc, label='X (pix)'),
                      bqplot.Axis(scale=line_y_y_sc, orientation='vertical', label=y_label)]
        line_y.scales['x'].min = x_min
        line_y.scales['x'].max = x_max
        x_min = max(int(x_min), 0)
        x_max = min(int(x_max), nx)
        zoomed_data_y = comp.data[y, x_min:x_max]
        if zoomed_data_y.size > 0:
            line_y.scales['y'].min = zoomed_data_y.min() * 0.95
            line_y.scales['y'].max = zoomed_data_y.max() * 1.05

        self.line_plot_across_x = fig_x
        self.line_plot_across_y = fig_y
        self.bqplot_figs_resize = self._figs
        self.plot_available = True
