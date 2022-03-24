from traitlets import Unicode, observe

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin

__all__ = ['Compass']


@tray_registry('imviz-compass', label="Imviz Compass")
class Compass(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "compass.vue"
    data_label = Unicode("").tag(sync=True)
    img_data = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)

    def _on_viewer_data_changed(self, msg=None):
        if self.viewer_selected:
            viewer = self.viewer.selected_obj
            viewer.on_limits_change()  # Force redraw

    @observe("viewer_selected", "plugin_opened")
    def _compass_with_new_viewer(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            # mixin object not yet initialized
            return

        # There can be only one!
        for vid, viewer in self.app._viewer_store.items():
            if vid == self.viewer.selected_id and self.plugin_opened:
                viewer.compass = self
                viewer.on_limits_change()  # Force redraw
            else:
                viewer.compass = None

    def clear_compass(self):
        """Clear the content of the plugin."""
        self.data_label = ''
        self.img_data = ''

    def draw_compass(self, data_label, img_data):
        """Draw compass in the plugin.
        Input is rendered buffer from Matplotlib.

        """
        self.data_label = data_label
        self.img_data = img_data
