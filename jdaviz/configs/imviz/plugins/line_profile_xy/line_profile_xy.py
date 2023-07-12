from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, Plot

__all__ = ['LineProfileXY']


@tray_registry('imviz-line-profile-xy', label="Imviz Line Profiles (XY)")
class LineProfileXY(PluginTemplateMixin):
    template_file = __file__, "line_profile_xy.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    selected_x = Any('').tag(sync=True)
    selected_y = Any('').tag(sync=True)

    plot_across_x_widget = Unicode().tag(sync=True)
    plot_across_y_widget = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_viewer = f'{self.app.config}-0'

        self.plot_across_x = Plot(self)
        self.plot_across_x.add_line('line', color='gray')
        self.plot_across_x.figure.axes[0].label = 'Y (pix)'
        self.plot_across_x_widget = 'IPY_MODEL_'+self.plot_across_x.model_id

        self.plot_across_y = Plot(self)
        self.plot_across_y.add_line('line', color='gray')
        self.plot_across_y.figure.axes[0].label = 'X (pix)'
        self.plot_across_y_widget = 'IPY_MODEL_'+self.plot_across_y.model_id

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
        self.plot_across_x.clear_all_marks()
        self.plot_across_y.clear_all_marks()

    # This is also triggered from viewer code.
    @observe("plugin_opened", "selected_viewer")
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

        self.plot_across_x.figure.title = f'X={x}'
        line_x = self.plot_across_x.marks['line']
        line_x.x, line_x.y = range(comp.data.shape[0]), comp.data[:, x]
        line_x.scales['x'].min, line_x.scales['x'].max = y_min, y_max
        self.plot_across_x.figure.axes[1].label = y_label

        y_min = max(int(y_min), 0)
        y_max = min(int(y_max), ny)
        zoomed_data_x = comp.data[y_min:y_max, x]
        if zoomed_data_x.size > 0:
            line_x.scales['y'].min = zoomed_data_x.min() * 0.95
            line_x.scales['y'].max = zoomed_data_x.max() * 1.05

        self.plot_across_y.figure.title = f'Y={y}'
        line_y = self.plot_across_y.marks['line']
        line_y.x, line_y.y = range(comp.data.shape[1]), comp.data[y, :]
        line_y.scales['x'].min, line_y.scales['x'].max = x_min, x_max
        self.plot_across_y.figure.axes[1].label = y_label

        x_min = max(int(x_min), 0)
        x_max = min(int(x_max), nx)
        zoomed_data_y = comp.data[y, x_min:x_max]
        if zoomed_data_y.size > 0:
            line_y.scales['y'].min = zoomed_data_y.min() * 0.95
            line_y.scales['y'].max = zoomed_data_y.max() * 1.05

        self.plot_available = True
