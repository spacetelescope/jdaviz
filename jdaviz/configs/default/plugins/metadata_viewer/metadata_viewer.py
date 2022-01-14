from copy import deepcopy

from traitlets import Bool, List, Unicode, observe

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['MetadataViewer']


@tray_registry('g-metadata-viewer', label="Metadata Viewer")
class MetadataViewer(TemplateMixin):
    template_file = __file__, "metadata_viewer.vue"
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode("").tag(sync=True)
    has_metadata = Bool(False).tag(sync=True)
    metadata = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

    def _on_viewer_data_changed(self, *args, **kwargs):
        self.dc_items = [data.label for data in self.app.data_collection]

    @observe("selected_data")
    def _show_metadata(self, event):
        try:
            data = self.app.data_collection[self.app.data_collection.labels.index(event['new'])]
        except IndexError:
            self.has_metadata = False
            self.metadata = []
            return

        if not hasattr(data, 'meta') or not isinstance(data.meta, dict) or len(data.meta) < 1:
            self.has_metadata = False
            self.metadata = []
        else:
            d = deepcopy(data.meta)
            for badkey in ('COMMENT', 'HISTORY', ''):
                if badkey in d:
                    del d[badkey]  # ipykernel cannot clean for JSON
            self.metadata = list(zip(d.keys(), map(str, d.values())))
            self.has_metadata = True
