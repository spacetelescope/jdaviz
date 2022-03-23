from traitlets import Any, List, Unicode, observe, Bool
from ipywidgets.widgets import widget_serialization

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                AddDataMessage, RemoveDataMessage)
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

    # Toggle for showing uncertainty in viewer
    show_uncertainty = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._on_data_changed())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._on_data_changed())

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    def _on_viewers_changed(self):
        self.viewer_items = self.app.get_viewer_ids()
        if self.selected_viewer not in self.viewer_items:
            # default to first entry, will trigger _on_viewer_select to set layer defaults
            self.selected_viewer = self.viewer_items[0] if len(self.viewer_items) else ""

    def _on_select_viewer_message(self, msg):
        # message from elsewhere requesting to change the selected viewer
        self.selected_viewer = msg.viewer

    def _on_data_changed(self):
        # Make sure new data has it's uncertainty plotted
        self._toggle_uncertainty(None)

    @observe("selected_viewer")
    def _selected_viewer_changed(self, event={}):
        viewer = self.app.get_viewer_by_id(event.get('new', self.selected_viewer))
        self.viewer_widget = viewer.viewer_options
        self.layer_widget = viewer.layer_options

    @observe("show_uncertainty")
    def _toggle_uncertainty(self, event):
        if self.app.state.settings.get("configuration") == "cubeviz":
            viewer = "cubeviz-3"
        elif self.app.state.settings.get("configuration") == "specviz":
            viewer = "specviz-0"
        else:
            return
        spec_viewer = self.app.get_viewer_by_id(viewer)

        if self.show_uncertainty:
            spec_viewer.show_uncertainties()
        else:
            spec_viewer._clean_error()
