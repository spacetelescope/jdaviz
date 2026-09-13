import numpy as np
from dataclasses import replace

from glue.core.hub import HubListener
from glue.core.message import DataCollectionDeleteMessage
from glue.core.subset import Subset

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                DataRenamedMessage, ViewerVisibleLayersChangedMessage)
from jdaviz.core.table_row_sync import (PluginTableRowSyncGroup,
                                        decode_row_sync_recipe,
                                        encode_row_sync_recipe)

__all__ = ['CatalogRowLinkManager', 'get_catalog_row_link_manager']

# key stored in a catalog's ``Data.meta`` mapping each generated column name to
# the viewer reference it populates on row click
_META_KEY = '_viewer_data_columns'
_PLUGIN_META_KEY = '_plugin_attribute_columns'


def _as_list(value):
    """Normalize a single cell value to a list.

    ``None`` -> ``[]``, a string -> ``[value]`` (or ``[]`` if empty), any other
    iterable -> ``list(value)``, and anything else -> ``[value]``.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    try:
        return list(value)
    except TypeError:
        return [value]


def get_catalog_row_link_manager(app):
    """Return the app's :class:`CatalogRowLinkManager`, creating it on first use.

    The manager is created lazily (e.g. on the first catalog import) and cached on
    ``app._catalog_row_link_manager`` so there is exactly one per application.
    """
    manager = getattr(app, '_catalog_row_link_manager', None)
    if manager is None:
        manager = CatalogRowLinkManager(app)
        app._catalog_row_link_manager = manager
    return manager


class CatalogRowLinkManager(HubListener):
    """App-level manager that links catalog table rows to viewer contents.

    Created once per app (lazily, on the first catalog import). The per-viewer
    ``"Data: <viewer>"`` columns are stored directly on the catalog's glue ``Data``
    (so they are shared by every table viewer showing that catalog, with no
    duplication) together with a ``data.meta['_viewer_data_columns']`` marker mapping
    each column to its viewer reference.

    The manager observes row highlighting on every table viewer; on click it clears
    and repopulates each listed viewer from the highlighted row's columns. It also
    keeps the columns in sync when a referenced dataset is renamed.
    """

    def __init__(self, app):
        self.app = app
        # viewer_id -> (viewer, checked callback, data callback) for table viewers
        self._observed = {}
        self._plugin_observers = {}
        self._applying_plugin_state = set()
        self._manager_hidden_columns = set()

        app.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)
        app.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewer_removed)
        app.hub.subscribe(self, DataRenamedMessage, handler=self._on_data_renamed)
        app.hub.subscribe(self, DataCollectionDeleteMessage,
                          handler=self._on_data_deleted)
        app.hub.subscribe(self, ViewerVisibleLayersChangedMessage,
                          handler=self._on_viewer_layers_changed)

        # attach checked observers to any table viewers that already exist
        for viewer in list(app._viewer_store.values()):
            self._setup_table_active_row_callbacks(viewer)

        # create any data-association columns needed for existing non-table viewers
        for viewer in list(app._viewer_store.values()):
            self._auto_create_column_for_viewer(viewer)
        self._reconcile_plugin_columns()

    def set_viewer_data_columns(self, data_label, viewer_data, column_prefix='Data: '):
        """Add/update per-viewer ``"<column_prefix><viewer>"`` columns on a catalog.

        Parameters
        ----------
        data_label : str
            Label of a catalog (loaded via the Catalog importer) in the data
            collection.
        viewer_data : dict
            Mapping of viewer reference (``str``) or viewer instance to the per-row
            data for that viewer. Each value is a list with one entry per catalog
            row; each entry is a data-collection label (``str``), a list of labels,
            or ``None``/empty for "no data in that viewer for that row".
        column_prefix : str
            Prefix used to build each column name (default ``"Data: "``).

        Returns
        -------
        list
            The names of the registered columns.

        Raises
        ------
        ValueError
            If ``data_label`` is not a catalog, a viewer cannot be resolved, or a
            per-viewer list does not have one entry per catalog row.
        """
        data = self.app.data_collection[data_label]
        if data.meta.get('_importer') != 'CatalogImporter':
            raise ValueError(f"Data '{data_label}' is not a catalog.")

        nrows = data.size
        columns = dict(data.meta.get(_META_KEY) or {})
        new_column_names = []
        for viewer, rows in viewer_data.items():
            # keys may be a viewer reference (str) or a viewer instance
            viewer_obj = (self.app.get_viewer(viewer) if isinstance(viewer, str)
                          else viewer)
            if viewer_obj is None:
                raise ValueError(f"Could not find viewer '{viewer}'.")
            viewer_ref = getattr(viewer_obj, 'reference', None) or viewer

            rows = list(rows)
            if len(rows) != nrows:
                raise ValueError(f"Data for viewer '{viewer_ref}' must have one entry "
                                 "per row in the catalog.")

            column_name = f"{column_prefix}{viewer_ref}"
            self._set_object_column(data, column_name, rows)
            columns[column_name] = viewer_ref
            new_column_names.append(column_name)

        data.meta[_META_KEY] = columns
        return new_column_names

    def _on_viewer_added(self, msg):
        viewer = self.app.get_viewer_by_id(msg.viewer_id)
        self._setup_table_active_row_callbacks(viewer)
        self._auto_create_column_for_viewer(viewer)

    def _on_viewer_removed(self, msg):
        entry = self._observed.pop(msg.viewer_id, None)
        if entry is not None:
            viewer, checked_callback, data_callback = entry
            try:
                viewer.widget_table.unobserve(checked_callback, names=['checked'])
                viewer.widget_table.unobserve(data_callback, names=['data'])
            except Exception:  # nosec
                pass

    def _on_data_renamed(self, msg):
        # the renamed dataset may be *referenced* by any catalog's columns, so
        # update every catalog that carries the marker meta
        for data in self.app.data_collection:
            columns = data.meta.get(_META_KEY) or {}
            for column_name in columns:
                self._rename_in_column(data, column_name, msg.old_label, msg.new_label)
            self._rewrite_plugin_data_reference(data, msg.old_label, msg.new_label)

    def _on_data_deleted(self, msg):
        deleted_label = getattr(getattr(msg, 'data', None), 'label', None)
        if deleted_label is None:
            return
        for data in self.app.data_collection:
            self._rewrite_plugin_data_reference(data, deleted_label, None)

    def _setup_table_active_row_callbacks(self, viewer):
        """Observe row-selection and table-data changes on a table viewer.

        No-op for non-table viewers and for table viewers we already observe.
        """
        if viewer is None or not hasattr(viewer, 'widget_table'):
            return
        vid = viewer.reference_id
        if vid in self._observed:
            return

        def checked_callback(change, _viewer=viewer):
            self._on_active_row_changed(_viewer, change)

        def data_callback(_change, _viewer=viewer):
            self._on_table_data_changed(_viewer)

        viewer.widget_table.observe(checked_callback, names=['checked'])
        viewer.widget_table.observe(data_callback, names=['data'])
        self._observed[vid] = (viewer, checked_callback, data_callback)

        # The table may already be holding catalog data by the time this
        # observer is attached (e.g. viewer created with an initial dataset).
        self._on_table_data_changed(viewer)

    def _on_active_row_changed(self, viewer, change):
        """Repopulate the listed viewers from the newly active (checked) row."""
        # Only react when the row-select tool is active; other tools (zoom,
        # highlight, subset) also use checked rows and should not trigger
        # row-link viewer repopulation.
        if hasattr(viewer, 'toolbar') and viewer.toolbar is not None:
            if viewer.toolbar.active_tool_id != 'jdaviz:table_row_select':
                return

        active_rows = change['new']
        # Only act on a single checked row (radio-button selection)
        if not active_rows or len(active_rows) != 1:
            return
        active_row = active_rows[0]

        # skip unless this table viewer is showing a catalog we manage (i.e. one
        # that set_viewer_data_columns has been called on); otherwise there is
        # nothing to link
        catalog_data = self._catalog_data_for_viewer(viewer)
        if catalog_data is None:
            return

        # column_to_viewer maps each "Data: <viewer>" column name -> the reference
        # of the viewer it drives (stored on the catalog's meta)
        column_to_viewer = catalog_data.meta.get(_META_KEY) or {}

        # labels currently in the data collection, used to skip any referenced
        # dataset that no longer exists
        available_labels = self.app.data_collection.labels
        for column_name, viewer_ref in column_to_viewer.items():
            if not self._is_column_synced_in_viewer(viewer, column_name):
                continue
            target_viewer = self.app.get_viewer(viewer_ref)
            if target_viewer is None:
                continue
            # the data labels this viewer should show for the active row
            try:
                assoc_data = catalog_data.get_component(column_name).data[active_row]
            except (KeyError, IndexError):
                assoc_data = []
            labels = [lbl for lbl in _as_list(assoc_data)
                      if lbl and lbl in available_labels]
            self._set_viewer_contents(target_viewer, labels)
        self._apply_plugin_columns(viewer, catalog_data, active_row)

    def _ensure_viewer_column(self, catalog, viewer_ref, column_name=None):
        """Ensure a ``Data: <viewer_ref>`` column exists on ``catalog``.

        Creates the column (filled with empty lists) and registers it in
        ``catalog.meta[_META_KEY]`` if not already present.
        """
        if column_name is None:
            column_name = f'Data: {viewer_ref}'
        nrows = catalog.size
        if column_name not in [c.label for c in catalog.components]:
            self._set_object_column(catalog, column_name, [[]] * nrows)
        columns = dict(catalog.meta.get(_META_KEY) or {})
        if column_name not in columns:
            columns[column_name] = viewer_ref
            catalog.meta[_META_KEY] = columns

    def _auto_create_column_for_viewer(self, viewer):
        """When a non-table viewer is added, auto-create ``Data:`` columns.

        For each table viewer that currently holds a catalog, a
        ``Data: <viewer_ref>`` column is added (if absent) and the toolbar
        visibility is refreshed so the ``TableRowSelect`` tool appears.
        """
        if viewer is None or hasattr(viewer, 'widget_table'):
            return
        viewer_ref = self._viewer_ref(viewer)
        if not viewer_ref:
            return
        column_name = f'Data: {viewer_ref}'
        for tv, _, _ in list(self._observed.values()):
            catalog = self._catalog_data_for_viewer(tv, require_managed=False)
            if catalog is None:
                continue
            self._ensure_viewer_column(catalog, viewer_ref, column_name)
            if hasattr(tv, 'toolbar') and tv.toolbar is not None:
                tv.toolbar._update_tool_visibilities()

    def _on_table_data_changed(self, table_viewer):
        """Called when a table viewer's catalog data changes.

        Creates ``Data:`` columns for every non-table viewer already in the
        app so the table is immediately ready for two-way sync.
        """
        table_data = getattr(getattr(table_viewer, 'widget_table', None), 'data', None)
        if table_data is not None and table_data.meta.get('_importer') == 'CatalogImporter':
            catalog = table_data
        else:
            catalog = self._catalog_data_for_viewer(table_viewer, require_managed=False)
        if catalog is None:
            return
        for viewer in list(self.app._viewer_store.values()):
            if hasattr(viewer, 'widget_table'):
                continue
            viewer_ref = self._viewer_ref(viewer)
            if not viewer_ref:
                continue
            self._ensure_viewer_column(catalog, viewer_ref)
        self._reconcile_plugin_columns(catalog)
        if hasattr(table_viewer, 'toolbar') and table_viewer.toolbar is not None:
            table_viewer.toolbar._update_tool_visibilities()

    def _on_viewer_layers_changed(self, msg):
        """Update the active table row when a non-table viewer's layers change.

        Writes the list of currently visible (non-subset) data labels back into
        the catalog's ``Data: <viewer_ref>`` column at the active row index so
        that selecting the same row later restores the exact viewer state.
        """
        viewer_ref = msg.viewer_reference
        viewer = self.app.get_viewer(viewer_ref)
        if viewer is None or hasattr(viewer, 'widget_table'):
            return
        column_name = f'Data: {viewer_ref}'
        for tv, _checked_cb, _data_cb in list(self._observed.values()):
            catalog = self._catalog_data_for_viewer(tv)
            if catalog is None:
                continue
            columns = catalog.meta[_META_KEY]
            if not columns or column_name not in columns:
                continue
            active_rows = tv.widget_table.checked
            if not active_rows:
                continue
            if not self._is_column_synced_in_viewer(tv, column_name):
                continue
            active_row = active_rows[0]
            visible_labels = self._get_visible_data_labels(viewer)
            try:
                values = list(catalog.get_component(column_name).data)
                values[active_row] = visible_labels
                self._set_object_column(catalog, column_name, values)
            except Exception:  # nosec
                pass

    @staticmethod
    def _is_column_synced_in_viewer(table_viewer, column_name):
        """False only when the viewer explicitly marks this column as de-synced."""
        state = getattr(table_viewer, 'state', None)
        if state is None or not hasattr(state, 'is_synced'):
            return True
        return state.is_synced(column_name)

    def _get_visible_data_labels(self, viewer):
        """Return the labels of all visible non-subset data layers in ``viewer``."""
        visible = []
        for layer in getattr(viewer, 'layers', []):
            layer_obj = getattr(layer, 'layer', None)
            if layer_obj is None or isinstance(layer_obj, Subset):
                continue
            if not layer.visible:
                continue
            label = getattr(layer_obj, 'label', None)
            if label:
                visible.append(label)
        return visible

    def _catalog_data_for_viewer(self, viewer, require_managed=True):
        """Return the catalog ``Data`` shown in ``viewer``, or ``None``.

        Parameters
        ----------
        require_managed : bool
            If ``True`` (default) only return a catalog that has been registered
            via :meth:`set_viewer_data_columns` (carries ``_META_KEY`` in its
            meta).  If ``False``, return any catalog loaded by the Catalog
            importer, including freshly imported ones with no link columns yet.
        """
        if require_managed:
            return self._first_layer_data(
                viewer, lambda d: _META_KEY in d.meta or _PLUGIN_META_KEY in d.meta
            )
        return self._first_layer_data(
            viewer, lambda d: d.meta.get('_importer') == 'CatalogImporter'
        )

    @staticmethod
    def _first_layer_data(viewer, condition_func):
        """Return the first layer's ``Data`` object that satisfies condition_func."""
        for layer in getattr(viewer, 'layers', []):
            data = getattr(getattr(layer, 'layer', None), 'data', None)
            if data is not None and condition_func(data):
                return data
        return None

    @staticmethod
    def _viewer_ref(viewer):
        """Return the reference string for viewer (try reference first, fallback on reference_id)"""
        return getattr(viewer, 'reference', None) or getattr(viewer, 'reference_id', None)

    def _set_object_column(self, data, column_name, values):
        """Add or update a column on ``data`` that stores a (list) value per row."""
        column_name = str(column_name)
        arr = np.empty(len(values), dtype=object)
        for i, v in enumerate(values):
            arr[i] = _as_list(v)
        if column_name in [c.label for c in data.components]:
            data.update_components({data.get_component(column_name): arr})
        else:
            data.add_component(arr, column_name)

    def _discover_plugin_declarations(self):
        plugins = []
        for item in getattr(self.app.state, 'tray_items', []):
            try:
                plugin = self.app.get_tray_item_from_name(item['name'])
            except (KeyError, TypeError):
                continue
            declarations = tuple(getattr(plugin, 'table_row_sync', ()))
            if declarations:
                plugins.append((plugin, declarations))
                self._observe_plugin(plugin, declarations)
        return plugins

    def _observe_plugin(self, plugin, declarations):
        if id(plugin) in self._plugin_observers:
            return
        callbacks = []
        for declaration in declarations:
            members = (declaration.members if isinstance(declaration, PluginTableRowSyncGroup)
                       else (declaration,))
            for member in members:
                def callback(change, _plugin=plugin, _declaration=declaration,
                             _member=member):
                    self._on_plugin_attribute_changed(_plugin, _declaration, _member, change)

                plugin.observe(callback, names=member.traitlet)
                callbacks.append((member.traitlet, callback))

        def relevance_callback(change, _plugin=plugin):
            if not change['new']:
                self._reconcile_plugin_columns()
            self._sync_plugin_column_visibility(_plugin)

        plugin.observe(relevance_callback, names='irrelevant_msg')
        callbacks.append(('irrelevant_msg', relevance_callback))
        self._plugin_observers[id(plugin)] = callbacks

    def _unobserve_plugin(self, plugin):
        for traitlet, callback in self._plugin_observers.pop(id(plugin), []):
            plugin.unobserve(callback, names=traitlet)

    def update_plugin_declarations(self, plugin, declarations):
        """Replace a plugin's runtime declarations and reconcile new columns."""
        self._unobserve_plugin(plugin)
        plugin.table_row_sync = tuple(declarations)
        self._observe_plugin(plugin, plugin.table_row_sync)
        self._reconcile_plugin_columns()

    def rename_plugin_selector(self, plugin, selector, old_value, new_value):
        """Migrate declarations and catalog columns after a selector entry rename."""
        old_declarations = tuple(getattr(plugin, 'table_row_sync', ()))
        new_declarations = []
        migrations = []
        for declaration in old_declarations:
            updated = declaration
            if isinstance(declaration, PluginTableRowSyncGroup):
                updated_members = tuple(
                    member.rename_selector(selector, old_value, new_value)
                    for member in declaration.members
                )
                updated = replace(declaration, members=updated_members)
                if declaration.label:
                    updated_label = declaration.label.replace(
                        f'[{selector}={old_value}]', f'[{selector}={new_value}]'
                    )
                    updated = replace(updated, label=updated_label)
            else:
                updated = declaration.rename_selector(selector, old_value, new_value)

            new_declarations.append(updated)
            if updated != declaration:
                migrations.append((declaration, updated))

        if not migrations:
            return
        plugin.table_row_sync = tuple(new_declarations)
        for old_declaration, new_declaration in migrations:
            old_name = self._column_label(plugin, old_declaration)
            new_name = self._column_label(plugin, new_declaration)
            for data in self._catalogs():
                metadata = dict(data.meta.get(_PLUGIN_META_KEY) or {})
                if old_name not in metadata:
                    continue
                if new_name in [component.label for component in data.components]:
                    raise ValueError(f"Plugin row-sync column collision: '{new_name}'")
                data.id[old_name].label = new_name
                metadata.pop(old_name)
                metadata[new_name] = self._declaration_meta(plugin, new_declaration)
                data.meta[_PLUGIN_META_KEY] = metadata

            for table_viewer, _checked_cb, _data_cb in self._observed.values():
                sync_state = dict(table_viewer.state.column_sync_state)
                if old_name in sync_state:
                    sync_state[new_name] = sync_state.pop(old_name)
                    table_viewer.state.column_sync_state = sync_state
                old_key = (table_viewer.reference_id, old_name)
                if old_key in self._manager_hidden_columns:
                    self._manager_hidden_columns.remove(old_key)
                    self._manager_hidden_columns.add((table_viewer.reference_id, new_name))
                if hasattr(table_viewer, '_update_component_permissions'):
                    table_viewer._update_component_permissions()

        self._unobserve_plugin(plugin)
        self._observe_plugin(plugin, plugin.table_row_sync)

    @staticmethod
    def _plugin_label(plugin):
        return getattr(plugin, '_registry_label', None) or getattr(plugin, '_plugin_name', None)

    @classmethod
    def _column_label(cls, plugin, declaration):
        if declaration.label:
            return declaration.label
        plugin_label = cls._plugin_label(plugin)
        if isinstance(declaration, PluginTableRowSyncGroup):
            return plugin_label
        selectors = ''
        if declaration.selectors:
            selectors = '[' + ','.join(f'{key}={value}'
                                       for key, value in declaration.selectors) + ']'
        return f'{plugin_label}{selectors}:{declaration.attribute}'

    @staticmethod
    def _declaration_meta(plugin, declaration):
        metadata = {'plugin': plugin._registry_name,
                    'direction': declaration.direction}
        if isinstance(declaration, PluginTableRowSyncGroup):
            metadata.update({
                'storage': 'json',
                'group': declaration.group,
                'members': [
                    {'attribute': member.attribute,
                     'value_kind': member.value_kind,
                     'manual_values': list(member.manual_values)}
                    for member in declaration.members
                ]
            })
        else:
            metadata.update({'storage': 'scalar',
                             'attribute': declaration.attribute,
                             'value_kind': declaration.value_kind,
                             'manual_values': list(declaration.manual_values)})
            if declaration.selectors:
                metadata['selectors'] = dict(declaration.selectors)
        return metadata

    def _catalogs(self):
        return [data for data in self.app.data_collection
                if data.meta.get('_importer') == 'CatalogImporter']

    @staticmethod
    def _read_plugin_declaration(plugin, declaration):
        if isinstance(declaration, PluginTableRowSyncGroup):
            values = plugin.read_table_row_sync_group(declaration)
            return encode_row_sync_recipe(values)
        return plugin.read_table_row_sync_attribute(declaration)

    def _reconcile_plugin_columns(self, catalog=None):
        catalogs = [catalog] if catalog is not None else self._catalogs()
        for plugin, declarations in self._discover_plugin_declarations():
            if plugin.irrelevant_msg:
                continue
            for declaration in declarations:
                column_name = self._column_label(plugin, declaration)
                target = self._declaration_meta(plugin, declaration)
                try:
                    value = self._read_plugin_declaration(plugin, declaration)
                except Exception:  # nosec
                    continue
                if isinstance(declaration, PluginTableRowSyncGroup):
                    decoded = decode_row_sync_recipe(value)
                    if any(member.value_kind == 'data_label'
                           and not member.manual_values
                           and not decoded.get(member.attribute)
                           for member in declaration.members):
                        continue
                for data in catalogs:
                    metadata = dict(data.meta.get(_PLUGIN_META_KEY) or {})
                    if column_name in metadata and metadata[column_name] != target:
                        raise ValueError(f"Plugin row-sync column collision: '{column_name}'")
                    component_labels = [component.label for component in data.components]
                    if column_name in component_labels and column_name not in metadata:
                        raise ValueError(f"Plugin row-sync column collision: '{column_name}'")
                    if column_name not in component_labels:
                        self._set_scalar_column(data, column_name, [value] * data.size)
                    metadata[column_name] = target
                    data.meta[_PLUGIN_META_KEY] = metadata
            for table_viewer, _checked_cb, _data_cb in self._observed.values():
                if hasattr(table_viewer, '_update_component_permissions'):
                    table_viewer._update_component_permissions()
                    self._sync_plugin_column_visibility(plugin)

    @staticmethod
    def _set_scalar_column(data, column_name, values):
        values = list(values)
        if all(value is None or isinstance(value, str) for value in values):
            array = np.asarray(['' if value is None else value for value in values], dtype=str)
        else:
            array = np.asarray(values)
        if column_name in [component.label for component in data.components]:
            data.update_components({data.get_component(column_name): array})
        else:
            data.add_component(array, column_name)

    def _on_plugin_attribute_changed(self, plugin, declaration, member, change):
        if id(plugin) in self._applying_plugin_state or plugin.irrelevant_msg:
            return
        if declaration.direction == 'to_plugin':
            return
        if (member.value_kind == 'data_label'
                and change.get('old')
                and change.get('old') not in member.manual_values
                and change.get('old') not in self.app.data_collection.labels):
            return

        value = self._read_plugin_declaration(plugin, declaration)
        column_name = self._column_label(plugin, declaration)
        if not any(column_name in [component.label for component in catalog.components]
                   for catalog in self._catalogs()):
            self._reconcile_plugin_columns()
        seen = set()
        for table_viewer, _checked_cb, _data_cb in self._observed.values():
            catalog = self._catalog_data_for_viewer(table_viewer, require_managed=False)
            active_rows = table_viewer.widget_table.checked
            if catalog is None or not active_rows:
                continue
            key = (id(catalog), active_rows[0])
            if key in seen or not self._is_column_synced_in_viewer(table_viewer, column_name):
                continue
            seen.add(key)
            try:
                values = list(catalog.get_component(column_name).data)
            except KeyError:
                continue
            if values[active_rows[0]] == value:
                continue
            values[active_rows[0]] = value
            self._set_scalar_column(catalog, column_name, values)

    def _apply_plugin_columns(self, table_viewer, catalog, active_row):
        metadata = catalog.meta.get(_PLUGIN_META_KEY) or {}
        declarations_by_plugin = {
            plugin._registry_name: (plugin, declarations)
            for plugin, declarations in self._discover_plugin_declarations()
        }
        for column_name, target in metadata.items():
            if not self._is_column_synced_in_viewer(table_viewer, column_name):
                continue
            plugin_entry = declarations_by_plugin.get(target.get('plugin'))
            if plugin_entry is None:
                continue
            plugin, declarations = plugin_entry
            if plugin.irrelevant_msg or target.get('direction') == 'from_plugin':
                continue
            declaration = next((item for item in declarations
                                if self._column_label(plugin, item) == column_name), None)
            if declaration is None:
                continue
            try:
                value = catalog.get_component(column_name).data[active_row]
                if isinstance(declaration, PluginTableRowSyncGroup):
                    value = decode_row_sync_recipe(value)
                elif value == '':
                    continue
                self._applying_plugin_state.add(id(plugin))
                if isinstance(declaration, PluginTableRowSyncGroup):
                    plugin.apply_table_row_sync_group(declaration, value)
                else:
                    plugin.apply_table_row_sync_attribute(declaration, value)
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            finally:
                self._applying_plugin_state.discard(id(plugin))

    def _sync_plugin_column_visibility(self, plugin):
        labels = {self._column_label(plugin, declaration)
                  for declaration in getattr(plugin, 'table_row_sync', ())}
        for table_viewer, _checked_cb, _data_cb in self._observed.values():
            catalog = self._catalog_data_for_viewer(table_viewer, require_managed=False)
            if catalog is None:
                continue
            hidden = list(table_viewer.state.hidden_components)
            for label in labels:
                try:
                    component_id = catalog.id[label]
                except KeyError:
                    continue
                key = (table_viewer.reference_id, label)
                if plugin.irrelevant_msg and component_id not in hidden:
                    hidden.append(component_id)
                    self._manager_hidden_columns.add(key)
                elif not plugin.irrelevant_msg and key in self._manager_hidden_columns:
                    hidden = [item for item in hidden if item is not component_id]
                    self._manager_hidden_columns.discard(key)
            table_viewer.state.hidden_components = hidden

    def _rewrite_plugin_data_reference(self, data, old_label, new_label):
        metadata = data.meta.get(_PLUGIN_META_KEY) or {}
        for column_name, target in metadata.items():
            try:
                values = list(data.get_component(column_name).data)
            except KeyError:
                continue
            changed = False
            if target.get('storage') == 'scalar' and target.get('value_kind') == 'data_label':
                manual_values = target.get('manual_values', [])
                new_values = []
                for value in values:
                    if value == old_label and value not in manual_values:
                        value = '' if new_label is None else new_label
                        changed = True
                    new_values.append(value)
            elif target.get('storage') == 'json':
                member_meta = {member['attribute']: member
                               for member in target.get('members', [])}
                new_values = []
                for value in values:
                    try:
                        recipe = decode_row_sync_recipe(value)
                    except ValueError:
                        new_values.append(value)
                        continue
                    for attribute, member in member_meta.items():
                        if (member.get('value_kind') == 'data_label'
                                and recipe.get(attribute) == old_label
                                and old_label not in member.get('manual_values', [])):
                            recipe[attribute] = new_label
                            changed = True
                    new_values.append(encode_row_sync_recipe(recipe))
            else:
                continue
            if changed:
                self._set_scalar_column(data, column_name, new_values)

    def _set_viewer_contents(self, viewer_obj, labels):
        """Show exactly ``labels`` in ``viewer_obj``, hiding anything else."""
        if len(labels):
            # add/show the first label and hide all other (non-target) layers
            self.app.add_data_to_viewer(viewer_obj.reference, labels[0],
                                        clear_other_data=True)
            # add/show the remaining target labels without hiding the ones above
            for label in labels[1:]:
                self.app.add_data_to_viewer(viewer_obj.reference, label)
            # reset the zoom limits so the newly-shown data fits in view
            if hasattr(viewer_obj, 'reset_limits'):
                viewer_obj.reset_limits()
        else:
            # no data for this viewer in this row: hide everything currently shown
            for layer in viewer_obj.layers:
                if layer.visible:
                    layer.visible = False

    def _rename_in_column(self, data, column_name, old_label, new_label):
        try:
            values = list(data.get_component(column_name).data)
        except KeyError:
            return
        changed = False
        new_values = []
        for cell in values:
            cell_list = _as_list(cell)
            if old_label in cell_list:
                cell_list = [new_label if v == old_label else v for v in cell_list]
                changed = True
            new_values.append(cell_list)
        if changed:
            self._set_object_column(data, column_name, new_values)
