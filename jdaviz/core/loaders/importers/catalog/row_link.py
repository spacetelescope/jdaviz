import numpy as np

from glue.core.hub import HubListener
from glue.core.subset import Subset

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                DataRenamedMessage, ViewerVisibleLayersChangedMessage)

__all__ = ['CatalogRowLinkManager', 'get_catalog_row_link_manager']

# key stored in a catalog's ``Data.meta`` mapping each generated column name to
# the viewer reference it populates on row click
_META_KEY = '_viewer_data_columns'


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
        # viewer_id -> (viewer, checked callback) for table viewers
        self._observed = {}

        app.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)
        app.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewer_removed)
        app.hub.subscribe(self, DataRenamedMessage, handler=self._on_data_renamed)
        app.hub.subscribe(self, ViewerVisibleLayersChangedMessage,
                          handler=self._on_viewer_layers_changed)

        # attach checked observers to any table viewers that already exist
        for viewer in list(app._viewer_store.values()):
            self._setup_table_active_row_callbacks(viewer)

        # create any data-association columns needed for existing non-table viewers
        for viewer in list(app._viewer_store.values()):
            self._auto_create_column_for_viewer(viewer)

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
            viewer, callback = entry
            try:
                viewer.widget_table.unobserve(callback, names=['checked'])
            except Exception:  # nosec
                pass

    def _on_data_renamed(self, msg):
        # the renamed dataset may be *referenced* by any catalog's columns, so
        # update every catalog that carries the marker meta
        for data in self.app.data_collection:
            columns = data.meta.get(_META_KEY)
            if not columns:
                continue
            for column_name in columns:
                self._rename_in_column(data, column_name, msg.old_label, msg.new_label)

    def _setup_table_active_row_callbacks(self, viewer):
        """Observe active-row (checked) changes on a table viewer.

        No-op for non-table viewers and for table viewers we already observe.
        """
        if viewer is None or not hasattr(viewer, 'widget_table'):
            return
        vid = viewer.reference_id
        if vid in self._observed:
            return

        def callback(change, _viewer=viewer):
            self._on_highlighted(_viewer, change)

        viewer.widget_table.observe(callback, names=['checked'])
        self._observed[vid] = (viewer, callback)

    def _on_highlighted(self, viewer, change):
        """Repopulate the listed viewers from the newly active (checked) row."""
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
        column_to_viewer = catalog_data.meta[_META_KEY]
        if not column_to_viewer:
            return

        # labels currently in the data collection, used to skip any referenced
        # dataset that no longer exists
        available_labels = self.app.data_collection.labels
        for column_name, viewer_ref in column_to_viewer.items():
            target_viewer = self.app.get_viewer(viewer_ref)
            if target_viewer is None:
                continue
            # the data labels this viewer should show for the active row
            try:
                raw = catalog_data.get_component(column_name).data[active_row]
            except (KeyError, IndexError):
                raw = []
            labels = [lbl for lbl in _as_list(raw) if lbl and lbl in available_labels]
            self._set_viewer_contents(target_viewer, labels)

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
        for tv_id, (tv, _cb) in list(self._observed.items()):
            catalog = self._catalog_data_for_viewer(tv, require_managed=False)
            if catalog is None:
                continue
            self._ensure_viewer_column(catalog, viewer_ref, column_name)
            if hasattr(tv, 'toolbar') and tv.toolbar is not None:
                tv.toolbar._update_tool_visibilities()

    def _on_table_data_changed(self, table_viewer):
        """Called when a table viewer's catalog data changes.

        Creates ``Data:`` columns for every non-table viewer already in the
        app so the table is immediately ready for two-way sync.  This only
        takes effect once the catalog already has at least one managed column
        (i.e. :meth:`set_viewer_data_columns` was called before), so that
        freshly-imported catalogs do not trigger premature column creation.
        """
        catalog = self._catalog_data_for_viewer(table_viewer)
        if catalog is None:
            return
        for viewer in list(self.app._viewer_store.values()):
            if hasattr(viewer, 'widget_table'):
                continue
            viewer_ref = self._viewer_ref(viewer)
            if not viewer_ref:
                continue
            self._ensure_viewer_column(catalog, viewer_ref)
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
        for tv_id, (tv, _cb) in list(self._observed.items()):
            catalog = self._catalog_data_for_viewer(tv)
            if catalog is None:
                continue
            columns = catalog.meta[_META_KEY]
            if not columns or column_name not in columns:
                continue
            active_rows = tv.widget_table.checked
            if not active_rows:
                continue
            active_row = active_rows[0]
            visible_labels = self._get_visible_data_labels(viewer)
            try:
                values = list(catalog.get_component(column_name).data)
                values[active_row] = visible_labels
                self._set_object_column(catalog, column_name, values)
            except Exception:  # nosec
                pass

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
            return self._first_layer_data(viewer, lambda d: _META_KEY in d.meta)
        return self._first_layer_data(
            viewer, lambda d: d.meta.get('_importer') == 'CatalogImporter'
        )

    @staticmethod
    def _first_layer_data(viewer, predicate):
        """Return the first layer's ``Data`` object that satisfies *predicate*, or ``None``."""
        for layer in getattr(viewer, 'layers', []):
            data = getattr(getattr(layer, 'layer', None), 'data', None)
            if data is not None and predicate(data):
                return data
        return None

    @staticmethod
    def _viewer_ref(viewer):
        """Return the canonical reference string for *viewer*."""
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
