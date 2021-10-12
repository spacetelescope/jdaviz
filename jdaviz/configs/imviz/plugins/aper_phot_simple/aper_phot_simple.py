from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue.core.subset import Subset
from traitlets import Bool, List

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import (NewViewerMessage, RemoveViewerMessage,
                                AddDataMessage, RemoveDataMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin):
    viewer_items = List(['imviz-0']).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, NewViewerMessage, handler=self._on_viewer_changed)
        self.hub.subscribe(self, RemoveViewerMessage, handler=self._on_viewer_changed)
        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self._selected_viewer_id = self.viewer_items[0]  # Start with default viewer
        self._selected_data = None
        self._selected_subset = None

    def _on_viewer_changed(self):
        self.viewer_items = self.app.get_viewer_ids(prefix='imviz')

        if self._selected_viewer_id not in self.viewer_items:
            self._selected_viewer_id = self.viewer_items[0]  # Should always have imviz-0
            self._on_viewer_data_changed()

    def _on_viewer_data_changed(self):
        # TODO: Do we really want to reset here?
        self.result_available = False
        self.results = []  # list of {'function': str, 'result': str}

        # NOTE: Unlike other plugins, this does not check viewer ID because
        # Imviz allows photometry from any number of open image viewers.
        viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
        self.dc_items = [lyr.layer.label for lyr in viewer.state.layers
                         if layer_is_image_data(lyr.layer)]
        self.subset_items = [lyr.layer.label for lyr in viewer.state.layers
                             if (isinstance(lyr.layer, Subset) and lyr.layer.ndim == 2)]

    def vue_viewer_selected(self, event):
        self._selected_viewer_id = event

    def vue_data_selected(self, event):
        self._selected_data = event

    def vue_subset_selected(self, event):
        self._selected_subset = event

    def vue_do_aper_phot(self, *args, **kwargs):
        pass
