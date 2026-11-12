"""
Temporary shim that bundles pending glue-jupyter changes into jdaviz until the
upstream PR is merged and a new release is pinned.

TO REVERT once upstream glue-jupyter is updated:
#   1. Delete this file and table_viewer.vue.
#   2. Revert the import and widget_table replacement in viewers.py
#      (search for "table_viewer").
  3. Update the glue-jupyter version pin.
"""

from echo import DictCallbackProperty
from glue_jupyter.table.viewer import TableGlue, TableState


# Track per-column row-linking sync-state
# Absent keys are synced; only de-synced columns are stored as False.
TableState.column_sync_state = DictCallbackProperty(
    docstring='Per column-label sync enable state; absent == True (synced)')


def _is_synced(self, column_label):
    return self.column_sync_state.get(str(column_label), True)


TableState.is_synced = _is_synced


class JdavizTableGlue(TableGlue):
    """Temporary TableGlue subclass bundling pending glue-jupyter changes."""

    template_file = (__file__, 'table_viewer.vue')

    def _get_headers(self):
        if self.data is None:
            return []
        components = self.get_visible_components()
        assoc_columns = set(self.data.meta.get('_viewer_data_columns') or {})
        viewer = getattr(self, 'jdaviz_viewer', None)
        app = getattr(viewer, 'jdaviz_app', None)
        state = getattr(app, 'state', None)
        dev_mos_loader = bool(getattr(state, 'dev_mos_loader', False))
        if not dev_mos_loader:
            components = [component for component in components
                          if str(component) not in assoc_columns]
        return [
            {
                'text': str(k),
                'value': str(k),
                'title': str(k),
                'key': str(k),
                'sortable': True,
                'editable': self.state is not None and self.state.is_editable(k),
                'renameable': self.state is not None and self.state.is_renameable(k),
                'removable': self.state is not None and self.state.is_removable(k),
                'toggleable_sync': str(k) in assoc_columns,
                'synced': self.state is None or self.state.is_synced(str(k)),
            }
            for k in components
        ]

    def add_column_renamed_callback(self, fn):
        """Register a callback invoked with (old_name, new_name) after a column rename."""
        if not hasattr(self, '_column_renamed_callbacks'):
            self._column_renamed_callbacks = []
        self._column_renamed_callbacks.append(fn)

    def vue_rename_column(self, data):
        """User accepted a column rename in the header text-input."""
        old_name = data.get('column', '')
        new_name = data.get('newName', '').strip()
        if not old_name or not new_name or old_name == new_name:
            return
        if self.data is not None and old_name in [c.label for c in self.data.main_components]:
            self.data.id[old_name].label = new_name
            for fn in getattr(self, '_column_renamed_callbacks', []):
                fn(old_name, new_name)
            self._update()

    def add_column_removed_callback(self, fn):
        """Register a callback invoked with (column_name,) after a column is removed."""
        if not hasattr(self, '_column_removed_callbacks'):
            self._column_removed_callbacks = []
        self._column_removed_callbacks.append(fn)

    def vue_remove_column(self, data):
        """User confirmed a column deletion via the remove-confirm badge."""
        label = data.get('column', '')
        if not label or self.data is None:
            return
        if label in [c.label for c in self.data.main_components]:
            cid = self.data.id[label]
            self.state.editable_components = [
                c for c in self.state.editable_components if c is not cid
            ]
            self.state.renameable_components = [
                c for c in self.state.renameable_components if c is not cid
            ]
            self.state.removable_components = [
                c for c in self.state.removable_components if c is not cid
            ]
            self.data.remove_component(cid)
            self._update()
        for fn in getattr(self, '_column_removed_callbacks', []):
            fn(label)

    def vue_toggle_column_sync(self, data):
        """Toggle the row-link sync state for a data-association column."""
        label = data.get('column', '')
        if not label or self.state is None:
            return
        current = self.state.column_sync_state.get(label, True)
        self.state.column_sync_state = {**self.state.column_sync_state, label: not current}


__all__ = ['JdavizTableGlue']
