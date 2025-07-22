from traitlets import Bool, Unicode, observe
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)

from jdaviz.core.events import NewViewerMessage, SnackbarMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, AutoTextField
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata

__all__ = ['BaseImporter', 'BaseImporterToDataCollection', 'BaseImporterToPlugin']


vid_map = {'spectrum-1d-viewer': '1D Spectrum',
           'spectrum-2d-viewer': '2D Spectrum',
           'imviz-image-viewer': 'Image'}


class BaseImporter(PluginTemplateMixin):
    # preference order of parsers, by registry name.  If empty, the first found match will
    # be used by default.  If not empty, the first match in the list will be used (including
    # over any parsers not included in the list).  If not empty but no valid parsers are in
    # the list, the first remaining match will be used.
    parser_preference = []

    def __init__(self, app, resolver, input, **kwargs):
        self._input = input
        self._resolver = resolver
        super().__init__(app, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    @property
    def is_valid(self):
        # override by subclass
        return False  # pragma: nocover

    @property
    def resolver(self):
        return self._resolver

    @property
    def input(self):
        return self._input

    @property
    def output(self):
        # override by subclass
        return self.input

    @property
    def target(self):
        raise NotImplementedError("Importer subclass must implement target")  # pragma: nocover

    def __call__(self):
        # override by subclass - should act on self.output and load into jdaviz
        raise NotImplementedError("Importer subclass must implement __call__")  # pragma: nocover

    @property
    def user_api(self):
        return ImporterUserApi(self)


class BaseImporterToDataCollection(BaseImporter):
    data_label_value = Unicode().tag(sync=True)
    data_label_default = Unicode().tag(sync=True)
    data_label_auto = Bool(True).tag(sync=True)
    data_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, resolver, input, **kwargs):
        super().__init__(app, resolver, input, **kwargs)
        self.data_label_default = self._registry_label
        self.data_label = AutoTextField(self, 'data_label_value',
                                        'data_label_default',
                                        'data_label_auto',
                                        'data_label_invalid_msg')

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=lambda _: self._on_label_changed())
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=lambda _: self._on_label_changed())
        self.observe(self._on_label_changed, 'data_label_value')
        self._on_label_changed()

    @property
    def default_viewer_reference(self):
        raise NotImplementedError("Importer subclass must implement default_viewer_reference")  # noqa pragma: nocover

    @property
    def ignore_viewers_with_cls(self):
        return ()

    @property
    def default_data_label_from_resolver(self):
        return self._resolver.default_label

    @property
    def default_viewer_label(self):
        return vid_map.get(self.default_viewer_reference, self.default_viewer_reference)

    @property
    def target(self):
        return {'type': 'viewer',
                'icon': 'mdi-window-maximize',
                'label': self.default_viewer_label}

    def _on_label_changed(self, msg={}):
        if not len(self.data_label_value.strip()):
            # strip will raise the same error for a label of all spaces
            self.data_label_invalid_msg = 'data_label must be provided'
            return

        # ensure the default label is unique for the data-collection
        self.data_label_default = self.app.return_unique_name(self.data_label_default)

        for data in self.app.data_collection:
            if self.data_label_value == data.label:
                self.data_label_invalid_msg = 'data_label already in use'
                return

        self.data_label_invalid_msg = ''

    @observe('data_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        self.resolver.import_disabled = len(self.data_label_invalid_msg) > 0

    def load_into_viewer(self, data_label, default_viewer_reference=None):
        added = 0
        for viewer in self.app._jdaviz_helper.viewers.values():
            if isinstance(viewer._obj, self.ignore_viewers_with_cls):
                continue
            if data_label in viewer.data_menu.data_labels_unloaded:
                added += 1
                viewer.data_menu.add_data(data_label)
            elif data_label in viewer.data_menu.data_labels_loaded:
                # was already loaded, increment count to avoid creating a new viewer
                added += 1
        if added == 0:
            if self.app.config not in ('deconfigged', 'lcviz'):
                # do not add additional viewers
                msg = SnackbarMessage(
                    "Data units are incompatible with viewer units, unload all data from viewer to add",  # noqa
                    color='error', sender=self, timeout=10000)
                self.app.hub.broadcast(msg)
                return
            if default_viewer_reference is None:
                default_viewer_reference = self.default_viewer_reference
                default_viewer_label = self.default_viewer_label
            else:
                default_viewer_label = vid_map.get(default_viewer_reference,
                                                   default_viewer_reference)
            default_viewer_label = self.app.return_unique_name(default_viewer_label,
                                                               typ='viewer')

            viewer_dict = viewer_registry.members.get(default_viewer_reference)
            viewer_cls = viewer_dict.get('cls')
            self.app._on_new_viewer(NewViewerMessage(viewer_cls, data=None, sender=self.app),
                                    vid=default_viewer_label,
                                    name=default_viewer_label,
                                    open_data_menu_if_empty=False)
            viewer = self.app._jdaviz_helper.viewers.get(default_viewer_label)
            viewer.data_menu.add_data(data_label)

    def add_to_data_collection(self, data, data_label=None,
                               parent=None, show_in_viewer=True, cls=None):
        if data_label is None:
            data_label = self.data_label_value.strip()
        if hasattr(data, 'meta'):
            try:
                data.meta = standardize_metadata(data.meta)
            except TypeError:
                pass
        self.app.add_data(data, data_label=data_label)
        if parent is not None:
            self.app._set_assoc_data_as_child(data_label, parent)
        # store the original input class so that get_data can default to the
        # same class as the input
        cls = cls if cls is not None else data.__class__
        self.app.data_collection[data_label]._native_data_cls = cls
        self.app.data_collection[data_label]._importer = self.__class__.__name__
        if show_in_viewer:
            self.load_into_viewer(data_label)

    def __call__(self, show_in_viewer=True):
        if self.data_label_invalid_msg:
            raise ValueError(self.data_label_invalid_msg)
        self.add_to_data_collection(self.output, show_in_viewer=show_in_viewer)


class BaseImporterToPlugin(BaseImporter):
    @property
    def default_plugin(self):
        raise NotImplementedError("Importer subclass must implement default_plugin")  # noqa pragma: nocover

    @property
    def target(self):
        return {'type': 'plugin',
                'icon': 'mdi-toy-brick-outline',
                'label': self.default_plugin}

    @property
    def has_default_plugin(self):
        return self.default_plugin in self.app._jdaviz_helper.plugins
