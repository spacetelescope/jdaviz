from traitlets import Unicode, List, observe

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                AddDataMessage, RemoveDataMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['Compass']


@tray_registry('imviz-compass', label="Imviz Compass")
class Compass(TemplateMixin):
    template_file = __file__, "compass.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    data_label = Unicode("").tag(sync=True)
    img_data = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)

        self._on_viewers_changed()  # Populate it on start-up

    def _on_viewers_changed(self, msg=None):
        self.viewer_items = self.app.get_viewer_ids()

        # Selected viewer was removed but Imviz always has a default viewer to fall back on.
        if self.selected_viewer not in self.viewer_items:
            self.selected_viewer = f'{self.app.config}-0'

    def _on_viewer_data_changed(self, msg=None):
        if self.selected_viewer:
            viewer = self.app.get_viewer_by_id(self.selected_viewer)
            viewer.on_limits_change()  # Force redraw

    @observe("selected_viewer")
    def _compass_with_new_viewer(self, *args, **kwargs):
        # There can be only one!
        for vid, viewer in self.app._viewer_store.items():
            if vid == self.selected_viewer:
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
