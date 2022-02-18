from traitlets import Any, Bool, Dict, Int, List, Unicode, observe

from glue.core.message import (SubsetCreateMessage, SubsetUpdateMessage, SubsetDeleteMessage)
from glue_jupyter.vuetify_helpers import link_glue, link_glue_choices

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

    # store a list of which widgets we want to show (based on the viewer type)
    # this gets populated automatically when the viewer selection changes, as do
    # the hooks between the glue-state and the traitlet items defined below
    # we'll need to do similar logic for layer_state_items
    viewer_state_items = List().tag(sync=True)

    # example of viewer bool state
    show_axes = Bool().tag(sync=True)

    # example of viewer choice state
    function_items = List().tag(sync=True)
    function_selected = Int(allow_none=True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda _: self._update_layer_items())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda _: self._update_layer_items())
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
    def _update_layer_items(self, event={}):
        def clear_glue_links(state_item):
            for handler in self._trait_notifiers.get(state_item, {}).get('change', []):
                if handler.__name__ == 'to_glue_state':
                    self.unobserve(handler, state_item)

        viewer = self.app.get_viewer(event.get('new', self.selected_viewer))
        self.viewer_state = viewer.state
        viewer_state_items = []
        for bool_state_item in ['show_axes']:
            clear_glue_links(bool_state_item)
            if hasattr(viewer.state, bool_state_item):
                viewer_state_items.append(bool_state_item)
                link_glue(self, bool_state_item, viewer.state)
        for choice_state_item in ['function']:
            clear_glue_links(choice_state_item)
            if hasattr(viewer.state, choice_state_item):
                viewer_state_items.append(choice_state_item)
                # NOTE: different arg order than link_glue...
                link_glue_choices(self, viewer.state, choice_state_item)
        self.viewer_state_items = viewer_state_items

        self.layer_items = [layer.layer.label for layer in viewer.layers]
        if self.selected_layer not in self.layer_items:
            self.selected_layer = self.layer_items[0] if len(self.layer_items) else ""

    @observe("selected_layer")
    def _update_layer_widget(self, event={}):
        viewer = self.app.get_viewer(self.selected_viewer)
        layer_label = event.get('new', self.selected_layer)
        layer_artist = [layer for layer in viewer.layers if layer.layer.label == layer_label][0]

        # here we would do similar and loop through the items we want to provide for layers
        # populate layer_state_items and handling unlinking/linking to the glue state
