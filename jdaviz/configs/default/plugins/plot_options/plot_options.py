from traitlets import Any, List, Unicode, observe
from ipywidgets.widgets import widget_serialization

from glue.core.message import (SubsetCreateMessage, SubsetUpdateMessage, SubsetDeleteMessage)

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                AddDataMessage, RemoveDataMessage,
                                PlotOptionsSelectViewerMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['PlotOptions']


def make_layer_panel(viewer, layer_artist):
    # modified from glue-jupyter layer_options.py
    widget_cls = viewer._layer_style_widget_cls
    if isinstance(widget_cls, dict):
        return widget_cls[type(layer_artist)](layer_artist.state)
    else:
        return widget_cls(layer_artist.state)


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin):
    template_file = __file__, "plot_options.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    layer_items = List([]).tag(sync=True)
    selected_layer = Unicode("").tag(sync=True)

    viewer_widget = Any().tag(sync=True, **widget_serialization)
    layer_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._selected_viewer_changed())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._selected_viewer_changed())
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda _: self._selected_viewer_changed())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda _: self._selected_viewer_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda _: self._selected_viewer_changed())
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
        self.layer_items = [layer.layer.label for layer in viewer.layers]
        if self.selected_layer not in self.layer_items:
            self.selected_layer = self.layer_items[0] if len(self.layer_items) else ""
        else:
            # we still need to force a refresh of the layer widget
            self._selected_layer_changed()

    @observe("selected_layer")
    def _selected_layer_changed(self, event={}):
        viewer = self.app.get_viewer(self.selected_viewer)
        layer_label = event.get('new', self.selected_layer)
        layer_artist = [layer for layer in viewer.layers if layer.layer.label == layer_label][0]
        self.layer_widget = make_layer_panel(viewer, layer_artist)
