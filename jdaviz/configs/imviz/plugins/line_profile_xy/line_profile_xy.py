from bqplot import pyplot as bqplt
from ipywidgets import widget_serialization
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin

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
        bqplt.clear()

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

        x_min, y_min, x_max, y_max = viewer._get_zoom_limits(data)
        comp = data.get_component(data.main_components[0])
        if comp.units:
            y_label = comp.units
        else:
            y_label = 'Value'

        _bqplt_clear_all()

        fig_x = bqplt.figure(1, title=f'X={x}',
                             fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                             title_style={'font-size': '12px'})
        bqplt.plot(comp.data[:, x], colors='gray', figure=fig_x)
        bqplt.xlim(y_min, y_max)
        y_min = max(int(y_min), 0)
        y_max = min(int(y_max), ny)
        zoomed_data_x = comp.data[y_min:y_max, x]
        bqplt.ylim(zoomed_data_x.min() * 0.95, zoomed_data_x.max() * 1.05)
        bqplt.xlabel(label='Y (pix)', mark=fig_x.marks[-1], figure=fig_x)
        bqplt.ylabel(label=y_label, mark=fig_x.marks[-1], figure=fig_x)
        self.line_plot_across_x = fig_x

        fig_y = bqplt.figure(2, title=f'Y={y}',
                             fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                             title_style={'font-size': '12px'})
        bqplt.plot(comp.data[y, :], colors='gray', figure=fig_y)
        bqplt.xlim(x_min, x_max)
        x_min = max(int(x_min), 0)
        x_max = min(int(x_max), nx)
        zoomed_data_y = comp.data[y, x_min:x_max]
        bqplt.ylim(zoomed_data_y.min() * 0.95, zoomed_data_y.max() * 1.05)
        bqplt.xlabel(label='X (pix)', mark=fig_y.marks[-1], figure=fig_y)
        bqplt.ylabel(label=y_label, mark=fig_y.marks[-1], figure=fig_y)
        self.line_plot_across_y = fig_y

        self.bqplot_figs_resize = [fig_x, fig_y]
        self.plot_available = True


def _bqplt_clear_all():
    """Clears hidden context of bqplot.pyplot module."""
    bqplt._context = {
        'figure': None,
        'figure_registry': {},
        'scales': {},
        'scale_registry': {},
        'last_mark': None,
        'current_key': None}
