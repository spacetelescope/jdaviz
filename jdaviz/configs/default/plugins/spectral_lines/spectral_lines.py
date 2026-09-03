from glue.core.message import DataCollectionAddMessage, DataCollectionDeleteMessage
from traitlets import List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, DataRenamedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin, LoadersMixin,
                                        EditableSelectPluginComponent)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['SpectralLines']


@tray_registry('g-spectral-lines', label="Spectral Lines", category="data:analysis")
class SpectralLines(PluginTemplateMixin, ViewerSelectMixin, LoadersMixin):
    template_file = __file__, "spectral_lines.vue"

    component_mode = Unicode().tag(sync=True)
    component_edit_value = Unicode().tag(sync=True)
    component_items = List().tag(sync=True)
    component_selected = Unicode().tag(sync=True)

    # redshift for all lines in the currently selected component. kept in sync
    # with the corresponding entry in self._components
    component_redshift = FloatHandleEmpty(0).tag(sync=True)

    # read-only: per-line info (name, rest, obs, show) for the currently
    # selected component, for display in the UI
    component_lines = List().tag(sync=True)

    # read-only: label of the data-collection table holding the spectral lines.
    # each component corresponds to a 'observed wavelength:<component>' column in
    # this table.
    line_table = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # maps component label to other info that is set per component (e.g redshift,
        # eventually plotting options). this is kept in sync with the component
        # select widget and is responsive to deleting or renaming components
        self._components = {}

        self._syncing_component_info = False

        self.viewer.add_filter('is_spectrum_viewer')

        self.component = EditableSelectPluginComponent(
            self,
            name='component',
            mode='component_mode',
            edit_value='component_edit_value',
            items='component_items',
            selected='component_selected',
            manual_options=['default'],
            on_add=self._on_component_add,
            on_rename=self._on_component_rename,
            on_remove=self._on_component_remove,
        )

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        # keep track of the spectral lines table in the data collection: pick up
        # a newly loaded line table, follow it if renamed, and drop the association
        # if it gets deleted.
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_collection_add)

        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_collection_delete)

        self.hub.subscribe(self, DataRenamedMessage,
                           handler=self._on_data_renamed)

        self.observe_traitlets_for_relevancy(
            traitlets_to_observe=['viewer_items'],
            irrelevant_msg_callback=self._irrelevant_msg_callback
        )

        self._plugin_description = 'Plot spectral lines.'
        self.docs_link = f'https://jdaviz.readthedocs.io/en/{self.vdocs}/plugins/spectral_lines.html'  # noqa

    def _irrelevant_msg_callback(self, *args):
        if not hasattr(self, 'viewer'):
            return None

        if not getattr(self._app.state, 'dev_spectral_lines_plugin', False):
            return 'Spectral Lines unavailable (requires dev_spectral_lines_plugin to be enabled)'

        has_spectrum_data = (len(self.viewer_items) > 0
                             and self.viewer.selected_obj is not None
                             and len(self.viewer.selected_obj.state.layers) > 0)

        if has_spectrum_data or self._table_viewer_has_line_table():
            return ''

        return ('Spectral Lines unavailable without either data loaded in a spectrum '
                'viewer or a line list loaded in a table viewer')

    def _table_viewer_has_line_table(self):
        """Whether any table viewer is currently displaying data loaded via the
        Spectral Line Database loader."""
        from jdaviz.configs.default.plugins.viewers import JdavizTableViewer
        for viewer in self._app._viewer_store.values():
            if not isinstance(viewer, JdavizTableViewer):
                continue
            for layer in viewer.state.layers:
                if getattr(layer.layer, 'meta', {}).get('_importer') == 'SpectralLinesImporter':
                    return True
        return False

    def _default_component_info(self):
        """Default entry stored per-component in ``self._components``."""
        # 'show' maps line-table row index to visibility (defaults to True)
        return {'redshift': 0.0, 'show': {}}

    @staticmethod
    def _component_col_name(lbl):
        """Name of the line-table column corresponding to a component."""
        return f'observed wavelength:{lbl}'

    def _get_line_table_data(self):
        """The glue Data object for the spectral lines table, or None."""
        if self.line_table and self.line_table in self._app.data_collection.labels:
            return self._app.data_collection[self.line_table]
        return None

    def _get_data_component_id(self, data, col_name):
        """ComponentID in ``data`` with label ``col_name``, or None."""
        for cid in data.components:
            if cid.label == col_name:
                return cid
        return None

    def _add_component_column(self, lbl, data=None):
        """
        Add or update the 'observed wavelength:<lbl>' column in the line table,
        applying the component's redshift to the table's original spectral
        location column (recomputed from the original values each time to
        avoid building up precision errors).
        """
        if data is None:
            data = self._get_line_table_data()
        if data is None:
            return

        source_col = data.meta.get('_jdaviz_loader_spectral_loc_col')
        source_cid = (self._get_data_component_id(data, source_col)
                      if source_col is not None else None)
        if source_cid is None:
            return

        redshift = self._components.get(lbl, self._default_component_info())['redshift']
        self._app._jdaviz_helper._set_data_component(
            data, self._component_col_name(lbl), data[source_cid] * (1 + redshift)
        )

    def _get_line_names(self, data):
        """Values of a line-name-like column in ``data``, or None."""
        for cid in data.components:
            if cid.label.lower() in ('linename', 'line_name', 'name', 'line', 'id', 'label'):
                comp = data.get_component(cid)
                # categorical (string) components store original values in .labels
                return comp.labels if hasattr(comp, 'labels') else data[cid]
        return None

    def _update_component_lines(self):
        """
        Rebuild ``component_lines`` (name, rest, observed wavelength, and
        visibility of each line) for the currently selected component.
        """
        data = self._get_line_table_data()
        source_col = (data.meta.get('_jdaviz_loader_spectral_loc_col')
                      if data is not None else None)
        source_cid = (self._get_data_component_id(data, source_col)
                      if source_col is not None else None)
        if source_cid is None:
            self.component_lines = []
            return

        if self.component_selected:
            info = self._components.setdefault(self.component_selected,
                                               self._default_component_info())
        else:
            info = self._default_component_info()

        rest_values = data[source_cid]
        unit = data.get_component(source_cid).units or ''
        names = self._get_line_names(data)

        self.component_lines = [
            {'linename': str(names[i]) if names is not None else f'Line {i + 1}',
             'rest': float(rest),
             'obs': float(rest) * (1 + info['redshift']),
             'unit': unit,
             'show': bool(info['show'].get(i, True))}
            for i, rest in enumerate(rest_values)
        ]

    def vue_toggle_line_visibility(self, line_ind):
        if not self.component_selected:
            return
        info = self._components.setdefault(self.component_selected,
                                           self._default_component_info())
        info['show'][line_ind] = not info['show'].get(line_ind, True)
        self._update_component_lines()

    def _remove_component_column(self, lbl):
        data = self._get_line_table_data()
        if data is None:
            return
        cid = self._get_data_component_id(data, self._component_col_name(lbl))
        if cid is not None:
            data.remove_component(cid)

    def _on_component_add(self, lbl):
        self._components.setdefault(lbl, self._default_component_info())
        self._add_component_column(lbl)

    def _on_component_rename(self, old_lbl, new_lbl):
        info = self._components.pop(old_lbl, self._default_component_info())
        self._components[new_lbl] = info

        # move the old column to the new name in the line table
        data = self._get_line_table_data()
        if data is None:
            return
        old_cid = self._get_data_component_id(data, self._component_col_name(old_lbl))
        if old_cid is None:
            return
        self._app._jdaviz_helper._set_data_component(
            data, self._component_col_name(new_lbl), data[old_cid]
        )
        data.remove_component(old_cid)

    def _on_component_remove(self, lbl):
        self._components.pop(lbl, None)
        self._remove_component_column(lbl)

    @observe('component_selected')
    def _on_component_selected_changed(self, change=None):
        # load the redshift for the newly-selected component into the traitlet,
        # creating a default entry the first time this component is seen
        if self.component_selected:
            info = self._components.setdefault(self.component_selected,
                                               self._default_component_info())
        else:
            # no component selected (encountered when removing the final component)
            info = self._default_component_info()

        self._syncing_component_info = True
        try:
            self.component_redshift = info['redshift']
        finally:
            self._syncing_component_info = False

        self._update_component_lines()

    @observe('component_redshift')
    def _on_component_redshift_changed(self, change):
        if self._syncing_component_info or not self.component_selected:
            # either this is us loading a value above (not a user edit), or there is
            # currently no selected component to store the value against
            return
        if self.component_redshift == '':
            return
        self._components.setdefault(self.component_selected, self._default_component_info())
        self._components[self.component_selected]['redshift'] = self.component_redshift
        # recompute this component's column from the original values
        self._add_component_column(self.component_selected)
        self._update_component_lines()

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('component', 'redshift'))

    def _on_viewer_data_changed(self, msg=None):
        self._set_relevant()
        if self.disabled_msg or self.irrelevant_msg:
            return

    def _on_data_collection_add(self, msg):
        # only interested in line-list tables
        data = msg.data
        if data.meta.get('_importer') != 'SpectralLinesImporter':
            return

        self.line_table = data.label

        # add a rest-wavelength column for every existing component
        for lbl in self.component.choices:
            self._components.setdefault(lbl, self._default_component_info())
            self._add_component_column(lbl, data=data)

        self._update_component_lines()

    def _on_data_collection_delete(self, msg):
        if msg.data.label == self.line_table:
            self.line_table = ''
            self._update_component_lines()

    def _on_data_renamed(self, msg):
        if msg.old_label == self.line_table:
            self.line_table = msg.new_label

    def _update_loader_items(self):
        # override to skip restrict_to_target: the Spectral Line Database loader
        # (and any other source loading spectral lines) uses BaseImporterToDataCollection
        # rather than BaseImporterToPlugin, so importers would never match this plugin's
        # target if restricted. Instead, just default the source to the Spectral Line
        # Database loader.

        def open_accordion():
            self.open_in_tray()
            self.loader_panel_ind = 0

        def close_accordion():
            self.loader_panel_ind = None

        def set_active_loader(resolver):
            self.loader_selected = resolver

        import jdaviz.core.loaders  # noqa
        from jdaviz.core.registries import loader_resolver_registry

        disabled_loaders = self._app.state.settings.get('disabled_loaders')
        if disabled_loaders is None:
            # Default: disable loaders based on server_is_remote setting
            if self._app.state.settings.get('server_is_remote', False):
                disabled_loaders = ['file', 'file drop', 'url', 'object',
                                    'astroquery', 'virtual observatory']
            else:
                disabled_loaders = []

        loader_items = []
        for name, Resolver in loader_resolver_registry.members.items():
            if name in disabled_loaders:
                continue
            loader = Resolver(app=self._app,
                              open_callback=open_accordion,
                              close_callback=close_accordion,
                              set_active_loader_callback=set_active_loader)
            loader_items.append({
                'name': name,
                'label': name,
                'requires_api_support': loader.requires_api_support,
                'widget': 'IPY_MODEL_' + loader.model_id
            })
        self.loader_items = loader_items

        default_name = 'spectral line database'
        if any(item['name'] == default_name for item in loader_items):
            self.loader_selected = default_name
        elif len(loader_items):
            self.loader_selected = loader_items[0]['name']
