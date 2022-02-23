from traitlets import Any, List, Unicode, observe
from ipywidgets.widgets import widget_serialization

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                PlotOptionsSelectViewerMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['PlotOptions']


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin):
    template_file = __file__, "plot_options.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)

    viewer_widget = Any().tag(sync=True, **widget_serialization)
    layer_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, PlotOptionsSelectViewerMessage,
                           handler=self._on_select_viewer_message)

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    def _on_viewers_changed(self):
        self.viewer_items = self.app.get_viewer_reference_names()
        if self.selected_viewer not in self.viewer_items:
            # default to first entry, will trigger _on_viewer_select to set layer defaults
            self.selected_viewer = self.viewer_items[0] if len(self.viewer_items) else ""

    def _on_select_viewer_message(self, msg):
        # message from elsewhere requesting to change the selected viewer
        self.selected_viewer = msg.viewer

    @observe("selected_viewer")
    def _selected_viewer_changed(self, event={}):
        viewer = self.app.get_viewer(event.get('new', self.selected_viewer))
        self.viewer_widget = viewer.viewer_options
        self.layer_widget = viewer.layer_options
