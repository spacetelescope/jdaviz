from astropy.io.fits import Header
from traitlets import Bool, List, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, DatasetSelectMixin

__all__ = ['MetadataViewer']


@tray_registry('g-metadata-viewer', label="Metadata Viewer")
class MetadataViewer(TemplateMixin, DatasetSelectMixin):
    template_file = __file__, "metadata_viewer.vue"
    has_metadata = Bool(False).tag(sync=True)
    metadata = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # override the default filters on dataset entries to require metadata in entries
        self.dataset.add_filter('not_from_plugin')

    @observe("dataset_selected")
    def _show_metadata(self, event):
        data = self.dataset.selected_dc_item
        if data is None or not hasattr(data, 'meta') or not isinstance(data.meta, dict) or len(data.meta) < 1: # noqa
            self.has_metadata = False
            self.metadata = []
            return

        if 'header' in data.meta and isinstance(data.meta['header'], (dict, Header)):
            if isinstance(data.meta['header'], Header):  # Specviz
                meta = dict(data.meta['header'])
            else:
                meta = data.meta['header']
        else:
            meta = data.meta

        d = flatten_nested_dict(meta)
        for badkey in ('COMMENT', 'HISTORY', ''):
            if badkey in d:
                del d[badkey]  # ipykernel cannot clean for JSON
        # TODO: Option to not sort?
        self.metadata = sorted(zip(d.keys(), map(str, d.values())))
        self.has_metadata = True


# TODO: If this is natively supported by asdf in the future, replace with native function.
# This code below is taken code from stdatamodels/model_base.py, and the method to_flat_dict()
def flatten_nested_dict(asdfnode, include_arrays=True):
    """
    Returns a dictionary of all of the schema items as a flat dictionary.
    Each dictionary key is a dot-separated name.  For example, the
    schema element ``meta.observation.date`` at the root node
    will end up in the dictionary as::

        { "meta.observation.date": "2012-04-22T03:22:05.432" }

    """
    import datetime
    import numpy as np
    from astropy.time import Time

    def convert_val(val):
        if isinstance(val, datetime.datetime):  # pragma: no cover
            return val.isoformat()
        elif isinstance(val, Time):  # pragma: no cover
            return str(val)
        return val

    if include_arrays:
        return dict((key, convert_val(val)) for (key, val) in _iteritems(asdfnode))
    else:  # pragma: no cover
        return dict((key, convert_val(val)) for (key, val) in _iteritems(asdfnode)
                    if not isinstance(val, np.ndarray))


def _iteritems(asdfnode):
    """
    Iterates over all of the schema items in a flat way.
    Each element is a pair (`key`, `value`).  Each `key` is a
    dot-separated name.  For example, the schema element
    `meta.observation.date` will end up in the result as::
        ("meta.observation.date": "2012-04-22T03:22:05.432")
    """
    def recurse(asdfnode, path=[]):
        if isinstance(asdfnode, dict):
            for key, val in asdfnode.items():
                for x in recurse(val, path + [key]):
                    yield x
        elif isinstance(asdfnode, (list, tuple)):
            for i, val in enumerate(asdfnode):
                for x in recurse(val, path + [i]):
                    yield x
        else:
            yield ('.'.join(str(x) for x in path), asdfnode)

    for x in recurse(asdfnode):
        yield x
