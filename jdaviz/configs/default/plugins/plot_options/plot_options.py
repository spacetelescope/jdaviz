from traitlets import Any, observe, Bool
from ipywidgets.widgets import widget_serialization

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin

__all__ = ['PlotOptions']


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin, ViewerSelectMixin):
    template_file = __file__, "plot_options.vue"

    viewer_widget = Any().tag(sync=True, **widget_serialization)
    layer_widget = Any().tag(sync=True, **widget_serialization)

    # Toggle for showing uncertainty in viewer
    show_uncertainty = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # populate the initial widgets
        self._viewer_selected_changed()

        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._on_data_changed())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._on_data_changed())

    def _on_data_changed(self):
        # Make sure new data has it's uncertainty plotted
        self._toggle_uncertainty(None)

    @observe("viewer_selected")
    def _viewer_selected_changed(self, event={}):
        if not hasattr(self, 'viewer'):
            # mixin object not yet initialized
            return

        viewer = self.viewer.selected_obj
        self.viewer_widget = viewer.viewer_options
        self.layer_widget = viewer.layer_options

    @observe("show_uncertainty")
    def _toggle_uncertainty(self, event):
        if self.app.state.settings.get("configuration") == "cubeviz":
            viewer = "cubeviz-3"
        elif self.app.state.settings.get("configuration") == "specviz":
            viewer = "specviz-0"
        elif self.app.state.settings.get("configuration") == "specviz2d":
            viewer = "specviz2d-1"
        elif self.app.state.settings.get("configuration") == "mosviz":
            viewer = "mosviz-2"
        else:
            return
        spec_viewer = self.app.get_viewer_by_id(viewer)

        if self.show_uncertainty:
            spec_viewer.show_uncertainties()
        else:
            spec_viewer._clean_error()
