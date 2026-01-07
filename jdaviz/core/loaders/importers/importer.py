import os
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
from jdaviz.utils import (standardize_metadata,
                          _wcs_only_label,
                          CONFIGS_WITH_LOADERS,
                          create_data_hash)

__all__ = ['BaseImporter', 'BaseImporterToDataCollection', 'BaseImporterToPlugin']


class BaseImporter(PluginTemplateMixin):
    # preference order of parsers, by registry name.  If empty, the first found match will
    # be used by default.  If not empty, the first match in the list will be used (including
    # over any parsers not included in the list).  If not empty but no valid parsers are in
    # the list, the first remaining match will be used.
    parser_preference = []

    import_disabled = Bool(False).tag(sync=True)
    import_spinner = Bool(False).tag(sync=True)

    existing_data_in_dc = List([]).tag(sync=True)

    def __init__(self, app, resolver, parser, input, **kwargs):
        self._input = input
        self._parser = parser
        self._resolver = resolver
        super().__init__(app, **kwargs)

        # Doing this in app instead of here avoids a lot of unnecessary overhead
        # from all the importers in memory
        self.app.observe(self._update_existing_data_in_dc_traitlet, 'existing_data_in_dc')
        self._update_existing_data_in_dc_traitlet()

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def _apply_kwargs(self, kwargs):
        user_api = self.user_api
        applied_kwargs = []
        for k, v in kwargs.items():
            if hasattr(user_api, k) and v is not None:
                setattr(user_api, k, v)
                applied_kwargs.append(k)

        return applied_kwargs

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

    def _update_existing_data_in_dc_traitlet(self, change={}):
        self.existing_data_in_dc = self.app.existing_data_in_dc

    def reset_and_check_existing_data_in_dc(self, change={}):
        """
        Check if the data to be imported appears to already exist in the data collection
        based on the data hash.  If so, update the existing_data_in_dc traitlet
        accordingly and display a warning snackbar message.
        """
        if not hasattr(self, 'data_hashes'):
            # If we do this here instead of at init, then we shouldn't get errors
            # from attempting to access unavailable importer attributes from 'output'
            self.data_hashes = [create_data_hash(self.output)]

        if not hasattr(self, 'hash_map_to_label'):
            self.hash_map_to_label = {dh: '' for dh in self.data_hashes}

        dc_labels = []
        loader_labels = []
        existing_data_in_dc = [(data.meta.get('_data_hash'),
                                data.label,
                                self.hash_map_to_label[data.meta.get('_data_hash')])
                               for data in self.app.data_collection
                               if data.meta.get('_data_hash') in self.data_hashes]

        if len(existing_data_in_dc) > 0:
            existing_data_in_dc, dc_labels, loader_labels = zip(*existing_data_in_dc)
        self.app.existing_data_in_dc = list(existing_data_in_dc)

        # Only need to display the message once
        if len(dc_labels) > 0:
            if any(self.hash_map_to_label.values()):
                msg = 'Selected data appears to be identical to existing data.\n'
                for dc_label, loader_label in zip(dc_labels, loader_labels):
                    msg += f"{loader_label} <=> {dc_label}\n"
            else:
                msg = (f"Selected data appears to be identical "
                       f"to existing data ({', '.join(dc_labels)}).")

            self.app.hub.broadcast(SnackbarMessage(msg.rstrip('\n'), sender=self, color='warning'))
            # TODO: Allow for now but implement a disabled message near the import button
            #  or indicate that the import will be a re-import And if allowing re-import,
            #  there's a bug that needs to be squashed... (second import doesn't show in viewer)
            #  but remains in app.
            # self.data_label_invalid_msg = msg

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
        self._resolver.load()


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

    def __init__(self, app, resolver, parser, input, **kwargs):
        super().__init__(app, resolver, parser, input, **kwargs)
        self.data_label = AutoTextField(self, 'data_label_value',
                                        'data_label_default',
                                        'data_label_auto',
                                        'data_label_invalid_msg')

        self.data_label_default = self.app.return_unique_name(self._registry_label)

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
        if self.app.config in ('deconfigged', 'imviz', 'lcviz', 'rampviz'):
            if self.app.config == 'imviz':
                # only allow image viewers
                supported_viewers = [item for item in supported_viewers
                                     if item.get('reference') == 'imviz-image-viewer']
            self.viewer_create_new_items = [item for item in supported_viewers
                                            if item.pop('allow_create', True)]

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
        raise NotImplementedError("Importer subclass must implement _get_supported_viewers")  # noqa pragma: nocover

    @property
    def ignore_viewers_with_cls(self):
        return ()

    @property
    def default_data_label_from_resolver(self):
        if self._resolver.parsed_input_is_query and self._resolver.treat_table_as_query:
            url = self._resolver.get_selected_url()
            path = os.path.splitext(os.path.basename(url.strip()))[0]
            if "product_name=" in path:
                path = path.split("product_name=")[1]
            return path
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
                self.data_label_invalid_msg = f"data_label='{self.data_label_value}' already in use"
                return

        self.data_label_invalid_msg = ''

    @observe('data_label_invalid_msg', 'viewer_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        self.import_disabled = (len(self.data_label_invalid_msg) > 0
                                or len(self.viewer_label_invalid_msg) > 0)

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return physical_type

    def add_to_data_collection(self, data, data_label=None, data_hash=None,
                               parent=None,
                               viewer_select=None,
                               cls=None):

        if data_label is None:
            data_label = self.data_label_value.strip()
        else:
            data_label = data_label.strip()

        if hasattr(data, 'meta'):
            try:
                data.meta = standardize_metadata(data.meta)
            except TypeError:
                pass

        # store the original input class so that get_data can default to the
        # same class as the input
        cls = cls if cls is not None else data.__class__
        if not hasattr(data, 'meta'):
            data.meta = {}
        if not isinstance(data.meta, dict):
            # ensure that data.meta is a dictionary and supports item assignment
            data.meta = dict(data.meta)
        data.meta['_native_data_cls'] = cls
        data.meta['_importer'] = self.__class__.__name__

        # Create a hashed representation of the data if not already present
        data.meta['_data_hash'] = data_hash if data_hash is not None else create_data_hash(data)

        self.app.add_data(data, data_label=data_label)
        if parent is not None:
            self.app._set_assoc_data_as_child(data_label, parent)

        def _physical_type_from_component(comp_id, comp):
            import astropy.units as u
            try:
                comp_units = comp.units
                if comp_units is None or comp_units == '':
                    return comp_units, None
                return comp_units, str(u.Unit(comp_units).physical_type)
            except (ValueError, TypeError, AttributeError):
                return comp_units, None

        new_dc_entry = self.app.data_collection[data_label]
        for comp_id in new_dc_entry.components:
            comp_units, physical_type = _physical_type_from_component(str(comp_id),
                                                                      new_dc_entry.get_component(comp_id))  # noqa
            comp_id._component_type = self.assign_component_type(str(comp_id),
                                                                 new_dc_entry.get_component(comp_id),  # noqa
                                                                 comp_units, physical_type)

        if self.app.config in CONFIGS_WITH_LOADERS:
            self.app._link_new_data_by_component_type(data_label)

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

        elif len(viewer_select.selected) == 0:
            # just send a snackbar as feedback
            if len(self.app._jdaviz_helper.viewers):
                msg = f"{data_label} loaded without any viewers selected - add manually from viewer data-menu"  # noqa
            else:
                msg = f"{data_label} loaded but no viewers were created.  Create viewers manually and add data from data-menu"  # noqa
            if not new_dc_entry.meta.get(_wcs_only_label, False):
                self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color='warning'))
        else:
            failed_viewers = []
            exceptions = []
            for viewer_label in viewer_select.selected:
                viewer = self.app._jdaviz_helper.viewers.get(viewer_label)
                try:
                    viewer.data_menu.add_data(data_label)
                except Exception as e:
                    failed_viewers.append(viewer_label)
                    exceptions.append(str(e))
            if len(failed_viewers) > 0:
                msg = f"Failed to add {data_label} to viewers: {', '.join(failed_viewers)}"
                self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color='error',
                                                       traceback=exceptions))

    @with_spinner('import_spinner')
    def __call__(self):
        if self.data_label_invalid_msg:
            raise ValueError(self.data_label_invalid_msg)
        if self.viewer.create_new.selected != '' and self.viewer_label_invalid_msg:
            raise ValueError(self.viewer_label_invalid_msg)
        # NOTE: if data hashing performance becomes an issue for importers that
        # don't overwrite __call__, we can pass the pre-computed hash from
        # self.data_hashes as a kwarg here
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
