from traitlets import Any, observe, Bool
from ipywidgets.widgets import widget_serialization

from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin

__all__ = ['PlotOptions']


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin, ViewerSelectMixin):
    template_file = __file__, "plot_options.vue"

    viewer_widget = Any().tag(sync=True, **widget_serialization)
    layer_widget = Any().tag(sync=True, **widget_serialization)

    # Whether the currently selected viewer has the ability to toggle uncertainty
    has_show_uncertainty = Bool(False).tag(sync=True)
    # Toggle for showing uncertainty in the currently selected viewer
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
        self.has_show_uncertainty = isinstance(viewer, SpecvizProfileView)
        if self.has_show_uncertainty:
            # TODO: refactor so that an API call to viewer.show_uncertainties, which would
            # set viewer.display_uncertainties would then update the widget state.
            self.show_uncertainty = viewer.display_uncertainties
        self.viewer_widget = viewer.viewer_options
        self.layer_widget = viewer.layer_options

    @observe("show_uncertainty")
    def _toggle_uncertainty(self, event):
        if not self.has_show_uncertainty:
            # the currently selected viewer does not support uncertainties
            return
        if self.show_uncertainty:
            self.viewer.selected_obj.show_uncertainties()
        else:
            self.viewer.selected_obj._clean_error()
