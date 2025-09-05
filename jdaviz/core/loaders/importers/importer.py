from traitlets import Any, Bool, List, Unicode, observe
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)

from jdaviz.core.events import NewViewerMessage, SnackbarMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        AutoTextField,
                                        ViewerSelectCreateNew,
                                        with_spinner)
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.utils import standardize_metadata

__all__ = ['BaseImporter', 'BaseImporterToDataCollection', 'BaseImporterToPlugin']


class BaseImporter(PluginTemplateMixin):
    # preference order of parsers, by registry name.  If empty, the first found match will
    # be used by default.  If not empty, the first match in the list will be used (including
    # over any parsers not included in the list).  If not empty but no valid parsers are in
    # the list, the first remaining match will be used.
    parser_preference = []

    import_disabled = Bool(False).tag(sync=True)
    import_spinner = Bool(False).tag(sync=True)

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

    def vue_import_clicked(self, *args, **kwargs):
        self.__call__()


class BaseImporterToDataCollection(BaseImporter):
    data_label_value = Unicode().tag(sync=True)
    data_label_default = Unicode().tag(sync=True)
    data_label_auto = Bool(True).tag(sync=True)
    data_label_invalid_msg = Unicode().tag(sync=True)

    viewer_create_new_items = List([]).tag(sync=True)
    viewer_create_new_selected = Unicode().tag(sync=True)

    viewer_items = List([]).tag(sync=True)
    viewer_selected = Any([]).tag(sync=True)
    viewer_multiselect = Bool(True).tag(sync=True)

    viewer_label_value = Unicode().tag(sync=True)
    viewer_label_default = Unicode().tag(sync=True)
    viewer_label_auto = Bool(True).tag(sync=True)
    viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, resolver, input, **kwargs):
        super().__init__(app, resolver, input, **kwargs)
        self.data_label_default = self._registry_label
        self.data_label = AutoTextField(self, 'data_label_value',
                                        'data_label_default',
                                        'data_label_auto',
                                        'data_label_invalid_msg')

        self.viewer = ViewerSelectCreateNew(self, 'viewer_items',
                                            'viewer_selected',
                                            'viewer_create_new_items',
                                            'viewer_create_new_selected',
                                            'viewer_label_value',
                                            'viewer_label_default',
                                            'viewer_label_auto',
                                            'viewer_label_invalid_msg',
                                            multiselect='viewer_multiselect',
                                            default_mode='empty')

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=lambda _: self._on_label_changed())
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=lambda _: self._on_label_changed())
        self._on_label_changed()

        supported_viewers = self._get_supported_viewers()
        if self.app.config == 'deconfigged':
            self.viewer_create_new_items = supported_viewers

        # for now, we'll use the same list of viewers that can be created
        # as the filter on existing viewers.  Eventually we may want this
        # to be more flexible so that custom viewers can show up in this
        # list (or both lists) without having to modify the importer - perhaps
        # by both viewers and importers describing their supported data shapes
        # and physical types
        def viewer_in_registry_names(viewer):
            classes = [viewer_registry.members.get(item.get('reference')).get('cls')
                       for item in supported_viewers]
            return isinstance(viewer, tuple(classes))
        self.viewer.add_filter(viewer_in_registry_names)
        self.viewer.select_default()

    @staticmethod
    def _get_supported_viewers():
        raise NotImplementedError("Importer subclass must implement viewer_create_new_items")  # noqa pragma: nocover

    @property
    def ignore_viewers_with_cls(self):
        return ()

    @property
    def default_data_label_from_resolver(self):
        return self._resolver.default_label

    @property
    def target(self):
        if len(self.viewer.create_new.choices) > 0:
            return {'type': 'viewer',
                    'icon': 'mdi-window-maximize',
                    'label': self.viewer.create_new.choices[0]}
        else:
            return {}

    @observe('data_label_value')
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

    @observe('data_label_invalid_msg', 'viewer_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        self.import_disabled = (len(self.data_label_invalid_msg) > 0
                                or len(self.viewer_label_invalid_msg) > 0)

    def add_to_data_collection(self, data, data_label=None,
                               parent=None,
                               viewer_select=None,
                               cls=None):
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

        viewer_select = viewer_select if viewer_select is not None else self.viewer
        if viewer_select.create_new.selected:
            viewer_reference = viewer_select.create_new.selected_item.get('reference')
            viewer_label = viewer_select.new_label.value.strip()

            viewer_dict = viewer_registry.members.get(viewer_reference)
            viewer_cls = viewer_dict.get('cls')
            self.app._on_new_viewer(NewViewerMessage(viewer_cls, data=None, sender=self.app),
                                    vid=viewer_label,
                                    name=viewer_label,
                                    open_data_menu_if_empty=False)
            viewer = self.app._jdaviz_helper.viewers.get(viewer_label)
            viewer.data_menu.add_data(data_label)

            # default to selecting this new viewer for next import
            viewer_select.create_new.selected = ''
            viewer_select.selected = [viewer_label]

        else:
            failed_viewers = []
            for viewer_label in viewer_select.selected:
                viewer = self.app._jdaviz_helper.viewers.get(viewer_label)
                try:
                    viewer.data_menu.add_data(data_label)
                except Exception:
                    failed_viewers.append(viewer_label)
            if len(failed_viewers) > 0:
                msg = f"Failed to add {data_label} to viewers: {', '.join(failed_viewers)}"
                self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color='error'))

    @with_spinner('import_spinner')
    def __call__(self):
        if self.data_label_invalid_msg:
            raise ValueError(self.data_label_invalid_msg)
        if self.viewer.create_new.selected != '' and self.viewer_label_invalid_msg:
            raise ValueError(self.viewer_label_invalid_msg)
        self.add_to_data_collection(self.output)


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
