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
            d = flatten_nested_dict(data.meta)
            for badkey in ('COMMENT', 'HISTORY', ''):
                if badkey in d:
                    del d[badkey]  # ipykernel cannot clean for JSON
            # TODO: Option to not sort?
            self.metadata = sorted(zip(d.keys(), map(str, d.values())))
            self.has_metadata = True


def _flatten_nested_dict_worker(d, parent_d=None, pfx=None):
    """ASDF metadata is nested dict.
    We have to flatten it so it displays nicely.
    Input is modified in-place.
    """
    for key in list(d.keys()):
        if isinstance(d[key], dict):
            out = _flatten_nested_dict_worker(d[key], d, key)
            if out is not None:
                new_key, val = out
                d[new_key] = val
            if len(d[key]) == 0:
                d.pop(key)
        elif pfx is not None and parent_d is not None:
            val = d.pop(key)
            return f'{pfx}.{key}', val


def flatten_nested_dict(orig_meta):
    """Return a copy of metadata that is flattened if the
    input is a nested dictionary.

    Example: ``meta = {'a': {'b': 1}}`` will become ``meta = {'a.b': 1}``.

    """
    meta = deepcopy(orig_meta)
    not_done = True
    while not_done:
        not_done = False
        _flatten_nested_dict_worker(meta)
        for key in list(meta.keys()):
            if isinstance(meta[key], dict):
                not_done = True
                break
    return meta
