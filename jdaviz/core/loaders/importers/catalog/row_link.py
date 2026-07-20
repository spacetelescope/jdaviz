import numpy as np

from glue.core.hub import HubListener

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                DataRenamedMessage)

__all__ = ['CatalogRowLinkManager', 'get_catalog_row_link_manager']

# key stored in a catalog's ``Data.meta`` mapping each generated column name to
# the viewer reference it populates on row click
_META_KEY = '_viewer_data_columns'


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
        # viewer_id -> (viewer, traitlets callback) for attached highlight observers
        self._observed = {}

        app.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)
        app.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewer_removed)
        app.hub.subscribe(self, DataRenamedMessage, handler=self._on_data_renamed)

        # attach to any table viewers that already exist
        for viewer in list(app._viewer_store.values()):
            self._setup_table_active_row_callbacks(viewer)

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
        if (getattr(data, 'meta', {}) or {}).get('_importer') != 'CatalogImporter':
            raise ValueError(f"Data '{data_label}' is not a catalog.")

        nrows = data.size
        columns = dict(data.meta.get(_META_KEY) or {})
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

        data.meta[_META_KEY] = columns
        return list(columns.keys())

    def _on_viewer_added(self, msg):
        self._setup_table_active_row_callbacks(self.app.get_viewer_by_id(msg.viewer_id))

    def _on_viewer_removed(self, msg):
        entry = self._observed.pop(msg.viewer_id, None)
        if entry is not None:
            viewer, callback = entry
            try:
                viewer.widget_table.unobserve(callback, names=['highlighted'])
            except Exception:  # nosec
                pass

    def _on_data_renamed(self, msg):
        # the renamed dataset may be *referenced* by any catalog's columns, so
        # update every catalog that carries the marker meta
        for data in self.app.data_collection:
            columns = (getattr(data, 'meta', {}) or {}).get(_META_KEY)
            if not columns:
                continue
            for column_name in columns:
                self._rename_in_column(data, column_name, msg.old_label, msg.new_label)

    def _setup_table_active_row_callbacks(self, viewer):
        """Observe active-row (highlighted) changes on a table viewer.

        No-op for non-table viewers and for table viewers we already observe.
        """
        if viewer is None or not hasattr(viewer, 'widget_table'):
            return
        vid = viewer.reference_id
        if vid in self._observed:
            return

        def callback(change, _viewer=viewer):
            self._on_highlighted(_viewer, change)

        viewer.widget_table.observe(callback, names=['highlighted'])
        self._observed[vid] = (viewer, callback)

    def _on_highlighted(self, viewer, change):
        """Repopulate the listed viewers from the newly active (highlighted) row."""
        active_row = change['new']
        if active_row is None or active_row < 0:
            return

        # skip unless this table viewer is showing a catalog we manage (i.e. one
        # that set_viewer_data_columns has been called on); otherwise there is
        # nothing to link
        catalog_data = self._catalog_data_for_viewer(viewer)
        if catalog_data is None:
            return

        # column_to_viewer maps each "Data: <viewer>" column name -> the reference
        # of the viewer it drives (stored on the catalog's meta)
        column_to_viewer = (getattr(catalog_data, 'meta', {}) or {}).get(_META_KEY)
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
            labels = [
                label
                for label in self._cell_as_list(catalog_data, column_name, active_row)
                if label and label in available_labels
            ]
            self._set_viewer_contents(target_viewer, labels)

    def _catalog_data_for_viewer(self, viewer):
        """Return the managed catalog ``Data`` shown in ``viewer``, or ``None``.

        A catalog becomes "managed" once :meth:`set_viewer_data_columns` stores the
        ``_viewer_data_columns`` marker (``_META_KEY``) in its ``Data.meta``; here we
        look through the viewer's layers for the first dataset carrying that marker.
        """
        for layer in getattr(viewer, 'layers', []):
            data = getattr(getattr(layer, 'layer', None), 'data', None)
            if data is not None and _META_KEY in (getattr(data, 'meta', {}) or {}):
                return data
        return None

    @staticmethod
    def _cell_as_list(data, column_name, row):
        """Return the (list) value of a cell, robust to missing columns/rows."""
        try:
            value = data.get_component(column_name).data[row]
        except (KeyError, IndexError):
            return []
        return list(value) if value is not None else []

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
            cell_list = list(cell) if cell is not None else []
            if old_label in cell_list:
                cell_list = [new_label if v == old_label else v for v in cell_list]
                changed = True
            new_values.append(cell_list)
        if changed:
            self._set_object_column(data, column_name, new_values)

    @staticmethod
    def _as_object_array(values):
        """Normalize each value to a list and pack them into an object-dtype array.

        Each entry becomes a list (``None`` -> ``[]``, a string -> ``[value]`` (or
        ``[]`` if empty), any other iterable -> ``list(value)``, else ``[value]``).
        Object dtype is required so the table can hold a list per row.
        """
        arr = np.empty(len(values), dtype=object)
        for i, value in enumerate(values):
            if value is None:
                arr[i] = []
            elif isinstance(value, str):
                arr[i] = [value] if value else []
            else:
                try:
                    arr[i] = list(value)
                except TypeError:
                    arr[i] = [value]
        return arr

    def _set_object_column(self, data, column_name, values):
        """Add or update a column on ``data`` that stores a (list) value per row."""
        column_name = str(column_name)
        arr = self._as_object_array(values)
        if column_name in [c.label for c in data.components]:
            data.update_components({data.get_component(column_name): arr})
        else:
            data.add_component(arr, column_name)
