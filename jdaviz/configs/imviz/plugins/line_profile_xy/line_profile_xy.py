from traitlets import Any, Bool, Unicode, observe

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, Plot

__all__ = ['LineProfileXY']


@tray_registry('imviz-line-profile-xy', label="Imviz Line Profiles (XY)")
class LineProfileXY(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "line_profile_xy.vue"
    uses_active_status = Bool(True).tag(sync=True)

    plot_available = Bool(False).tag(sync=True)
    selected_x = Any('').tag(sync=True)
    selected_y = Any('').tag(sync=True)

    plot_across_x_widget = Unicode().tag(sync=True)
    plot_across_y_widget = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plot_across_x = Plot(self)
        self.plot_across_x.add_line('line', color='gray')
        self.plot_across_x.figure.axes[0].label = 'Y (pix)'
        self.plot_across_x_widget = 'IPY_MODEL_'+self.plot_across_x.model_id

        self.plot_across_y = Plot(self)
        self.plot_across_y.add_line('line', color='gray')
        self.plot_across_y.figure.axes[0].label = 'X (pix)'
        self.plot_across_y_widget = 'IPY_MODEL_'+self.plot_across_y.model_id

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def reset_results(self):
        self.plot_available = False
        self.plot_across_x.clear_all_marks()
        self.plot_across_y.clear_all_marks()

    def _create_viewer_callbacks(self, viewer):
        if not self.is_active:
            return

        callback = self._viewer_callback(viewer, self._on_viewer_key_event)
        viewer.add_event_callback(callback, events=['keydown'])

    def _on_viewer_added(self, msg):
        self._create_viewer_callbacks(self.app.get_viewer_by_id(msg.viewer_id))

    @observe('is_active')
    def on_is_active_changed(self, *args):
        # subscribe/unsubscribe to keypress events across all viewers
        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                # table viewer, etc
                continue
            callback = self._viewer_callback(viewer, self._on_viewer_key_event)

            if self.is_active:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)

        if self.is_active:
            self.vue_draw_plot()

    def _on_viewer_key_event(self, viewer, data):
        if data['key'] == 'l':
            image = viewer.active_image_layer.layer
            x = data['domain']['x']
            y = data['domain']['y']
            if x is None or y is None:  # Out of bounds
                return
            x, y, _, _ = viewer._get_real_xy(image, x, y)
            self.selected_x = x
            self.selected_y = y
            self.viewer_selected = viewer.reference_id
            # TODO: remove manual calls to vue_draw_plot and trigger
            # by changes to selected_x/selected_y as well as viewer_selected
            self.vue_draw_plot()

    @observe("viewer_selected")
    def vue_draw_plot(self, *args, **kwargs):
        """Draw line profile plots for given Data across given X and Y indices (0-indexed)."""
        if not self.selected_x or not self.selected_y or not self.is_active:
            return

        viewer = self.viewer.selected_obj
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
