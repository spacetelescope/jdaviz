from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer

from jdaviz.core.events import PlotOptionsSelectViewerMessage
from jdaviz.core.registries import viewer_registry

__all__ = ['JdavizViewerMixin']

viewer_registry.add("g-profile-viewer", label="Profile 1D", cls=BqplotProfileView)
viewer_registry.add("g-image-viewer", label="Image 2D", cls=BqplotImageView)
viewer_registry.add("g-table-viewer", label="Table", cls=TableViewer)


class JdavizViewerMixin:
    @property
    def jdaviz_app(self):
        """The Jdaviz application tied to the viewer."""
        return self.session.jdaviz_app

    @property
    def jdaviz_helper(self):
        """The Jdaviz configuration helper tied to the viewer."""
        return self.jdaviz_app._jdaviz_helper

    @property
    def reference_name(self):
        # TODO: this should probably be stored instead of this hideously hacky loop
        for reference in self.jdaviz_app.get_viewer_reference_names():
            if self.jdaviz_app.get_viewer(reference) == self:
                return reference
        return None

    def open_plot_options(self):
        """Open plot options for this viewer in the app sidebar"""
        self.jdaviz_app.state.drawer = True
        tray_item_labels = [tray_item['label'] for tray_item in self.jdaviz_app.state.tray_items]
        index = tray_item_labels.index('Plot Options')
        if index not in self.jdaviz_app.state.tray_items_open:
            self.jdaviz_app.state.tray_items_open = self.jdaviz_app.state.tray_items_open + [index]
        msg = PlotOptionsSelectViewerMessage(sender=self, viewer=self.reference_name)
        self.session.hub.broadcast(msg)
