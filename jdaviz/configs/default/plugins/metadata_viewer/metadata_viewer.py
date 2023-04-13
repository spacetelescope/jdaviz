from traitlets import Any, Bool, List, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY

__all__ = ['MetadataViewer']


@tray_registry('g-metadata-viewer', label="Metadata")
class MetadataViewer(PluginTemplateMixin, DatasetSelectMixin):
    """
    See the :ref:`Metadata Viewer Plugin Documentation <imviz_metadata-viewer>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to expose the metadata.
    * :attr:`show_primary`:
      Whether to show MEF primary header metadata instead.
    * :attr:`metadata`:
      Read-only metadata. If the data is loaded from a multi-extension FITS file,
      this can be the extension header or the primary header, depending on
      ``show_primary`` setting.

    """
    template_file = __file__, "metadata_viewer.vue"
    has_metadata = Bool(False).tag(sync=True)
    has_primary = Bool(False).tag(sync=True)
    show_primary = Bool(False).tag(sync=True)
    has_comments = Bool(False).tag(sync=True)
    metadata = List([]).tag(sync=True)
    metadata_filter = Any().tag(sync=True)  # string or None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # override the default filters on dataset entries to require metadata in entries
        self.dataset.add_filter('not_from_plugin')

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'show_primary'), readonly=('metadata',))

    def reset(self):
        self.has_metadata = False
        self.has_primary = False
        self.show_primary = False
        self.has_comments = False
        self.metadata = []

    @observe("dataset_selected")
    def show_metadata(self, event):
        data = self.dataset.selected_dc_item
        if (data is None or not hasattr(data, 'meta') or not isinstance(data.meta, dict)
                or len(data.meta) < 1):
            self.reset()
            return

        if PRIHDR_KEY in data.meta:
            self.has_primary = True
        else:
            self.has_primary = False
            self.show_primary = False

        self.find_public_metadata(data.meta, primary_only=self.show_primary)

    @observe("show_primary")
    def handle_show_primary(self, event):
        if not self.show_primary:
            self.show_metadata(event)
            return

        data = self.dataset.selected_dc_item
        if (data is None or not hasattr(data, 'meta') or not isinstance(data.meta, dict)
                or len(data.meta) < 1):
            self.reset()
            return

        self.find_public_metadata(data.meta, primary_only=True)

    def find_public_metadata(self, meta, primary_only=False):
        if primary_only:
            if PRIHDR_KEY in meta:
                meta = meta[PRIHDR_KEY]
            else:
                self.reset()
                return

        d = flatten_nested_dict(meta)
        # Some FITS keywords cause "# ipykernel cannot clean for JSON" messages.
        # Also, we want to hide internal metadata that starts with underscore.
        badkeys = ['COMMENT', 'HISTORY', ''] + [k for k in d if k.startswith('_')]
        for badkey in badkeys:
            if badkey in d:
                del d[badkey]

        if COMMENTCARD_KEY in meta:
            has_comments = True

            def get_comment(key):
                if key in meta[COMMENTCARD_KEY]._header:
                    val = meta[COMMENTCARD_KEY][key]
                else:
                    val = ''
                return val
        else:
            has_comments = False

            def get_comment(key):
                return ''

        # TODO: Option to not sort?
        public_meta = sorted(zip(d.keys(), map(str, d.values()), map(get_comment, d.keys())))
        if len(public_meta) > 0:
            self.metadata = public_meta
            self.has_metadata = True
            self.has_comments = has_comments
        else:
            self.reset()


# TODO: If this generalized in stdatamodels in the future, replace with native function.
#       See https://github.com/spacetelescope/stdatamodels/issues/131
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
