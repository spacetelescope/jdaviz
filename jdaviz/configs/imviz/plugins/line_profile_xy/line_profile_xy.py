from bqplot import pyplot as bqplt
from ipywidgets import widget_serialization
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['LineProfileXY']


@tray_registry('imviz-line-profile-xy', label="Imviz Line Profiles (XY)")
class LineProfileXY(TemplateMixin):
    template_file = __file__, "line_profile_xy.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    line_plot_across_x = Any('').tag(sync=True, **widget_serialization)
    line_plot_across_y = Any('').tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ix = None
        self._iy = None

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)

        self._on_viewers_changed()  # Populate it on start-up

    def _on_viewers_changed(self, msg=None):
        self.viewer_items = self.app.get_viewer_ids()

        # Selected viewer was removed but Imviz always has a default viewer to fall back on.
        if self.selected_viewer not in self.viewer_items:
            self.selected_viewer = f'{self.app.config}-0'

    @observe("selected_viewer")
    def _replot_with_new_viewer(self, *args, **kwargs):
        if self._ix is None or self._iy is None:
            self.reset_results()
            return

        viewer = self.app.get_viewer_by_id(self.selected_viewer)
        viewer.on_mouse_or_key_event({
            'event': 'keydown',
            'key': 'l',
            'domain': {'x': self._ix, 'y': self._iy}})

    def reset_results(self):
        self.plot_available = False
        self.line_plot_across_x = ''
        self.line_plot_across_y = ''
        bqplt.clear()

    def plot_lines(self, data, x, y):
        """Draw line profile plots for given Data across given X and Y indices (0-indexed)."""
        self._ix = x
        self._iy = y
        if x < 0 or y < 0 or x >= data.shape[1] or y >= data.shape[0]:
            self.reset_results()
            return

        comp = data.get_component(data.main_components[0])
        if comp.units:
            y_label = comp.units
        else:
            y_label = 'Value'

        _clear_figure(1)
        fig_x = bqplt.figure(1, title=f'X={x}',
                             fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                             title_style={'font-size': '12px'})
        bqplt.plot(comp.data[:, x], colors='gray', figure=fig_x)
        bqplt.xlabel(label='Y', mark=fig_x.marks[-1], figure=fig_x)
        bqplt.ylabel(label=y_label, mark=fig_x.marks[-1], figure=fig_x)
        self.line_plot_across_x = fig_x

        _clear_figure(2)
        fig_y = bqplt.figure(2, title=f'Y={y}',
                             fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                             title_style={'font-size': '12px'})
        bqplt.plot(comp.data[y, :], colors='gray', figure=fig_y)
        bqplt.xlabel(label='X', mark=fig_y.marks[-1], figure=fig_y)
        bqplt.ylabel(label=y_label, mark=fig_y.marks[-1], figure=fig_y)
        self.line_plot_across_y = fig_y

        self.bqplot_figs_resize = [fig_x, fig_y]
        self.plot_available = True


def _clear_figure(key):
    """Clears the figure tied to given key of all marks axes and grid lines."""
    fig = bqplt._context['figure_registry'].get(key)
    if fig is not None:
        fig.marks = []
        fig.axes = []
        setattr(fig, 'axis_registry', {})
        bqplt._context['scales'] = {}
        if key == bqplt._context['current_key']:
            bqplt._context['scale_registry'][key] = {}
