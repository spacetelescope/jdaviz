from traitlets import Any, Bool, Unicode, observe

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin, Plot,
                                        skip_if_no_updates_since_last_active)

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
        self.plot_across_x.figure.axes[0].label = 'Y (pix)'
        self.plot_across_x_widget = 'IPY_MODEL_'+self.plot_across_x.model_id

        self.plot_across_y = Plot(self)
        self.plot_across_y.figure.axes[0].label = 'X (pix)'
        self.plot_across_y_widget = 'IPY_MODEL_'+self.plot_across_y.model_id

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def reset_results(self):
        self.plot_available = False
        self.plot_across_x.update_style('line', visible=False)
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
    def _is_active_changed(self, msg):
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

        # pass along the msg object so that @skip_if_no_updates_since_last_active can be used
        # to avoid re-drawing if no changes since the last time is_active was set
        self.vue_draw_plot(msg)

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
    @skip_if_no_updates_since_last_active()  # called with msg passed along from _is_active_changed
    def vue_draw_plot(self, msg={}):
        """Draw line profile plots for given Data across given X and Y indices (0-indexed)."""
        if not self.selected_x or not self.selected_y:
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

        comp = data.get_component(data.main_components[0])
        if comp.units:
            y_label = comp.units
        else:
            y_label = 'Value'

        self.plot_across_x.figure.title = f'X={x}'
        self.plot_across_x._update_data('line', x=range(comp.data.shape[0]), y=comp.data[:, x],
                                        reset_lims=True)
        self.plot_across_x.update_style('line', line_visible=True,
                                        markers_visible=False, color='gray')
        self.plot_across_x.figure.axes[1].label = y_label

        self.plot_across_y.figure.title = f'Y={y}'
        self.plot_across_y._update_data('line', x=range(comp.data.shape[1]), y=comp.data[y, :],
                                        reset_lims=True)
        self.plot_across_y.update_style('line', line_visible=True,
                                        markers_visible=False, color='gray')
        self.plot_across_y.figure.axes[1].label = y_label

        self.plot_available = True
