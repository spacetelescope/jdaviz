from traitlets import List, Unicode

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['ExportViewer']


@tray_registry('g-export-viewer', label="Export Plot")
class ExportViewer(TemplateMixin):
    template_file = __file__, "export_viewer.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    def _on_viewers_changed(self):
        self.viewer_items = self.app.get_viewer_ids()
        if self.selected_viewer not in self.viewer_items:
            # default to first entry, will trigger _on_viewer_select to set layer defaults
            self.selected_viewer = self.viewer_items[0] if len(self.viewer_items) else ""

    def vue_save_figure(self, filetype):
        """
        Callback for save figure events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        viewer = self.app.get_viewer_by_id(self.selected_viewer)
        if filetype == "png":
            viewer.figure.save_png()
        elif filetype == "svg":
            viewer.figure.save_svg()
