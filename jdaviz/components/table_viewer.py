"""
Temporary shim that bundles pending glue-jupyter changes into jdaviz until the
upstream PR is merged and a new release is pinned.

TO REVERT once upstream glue-jupyter is updated:
#   1. Delete this file and table_viewer.vue.
#   2. Revert the import and widget_table replacement in viewers.py
#      (search for "table_viewer").
  3. Update the glue-jupyter version pin.
"""

from echo import ListCallbackProperty
from glue_jupyter.table.viewer import TableGlue, TableState, TableViewer


# ---------------------------------------------------------------------------
# Patch TableState — adds renameable_components / removable_components.
# Guards against double-patching (e.g. pytest re-imports).
# ---------------------------------------------------------------------------

if not hasattr(TableState, 'renameable_components'):
    TableState.renameable_components = ListCallbackProperty(
        docstring='Attributes whose column header can be renamed')
    TableState.removable_components = ListCallbackProperty(
        docstring='Attributes whose column can be removed from the table')

    def _is_renameable(self, component_id):
        """Check if a component's header can be renamed (identity comparison)."""
        for cid in self.renameable_components:
            if component_id is cid:
                return True
        return False

    def _is_removable(self, component_id):
        """Check if a component can be removed from the table (identity comparison)."""
        for cid in self.removable_components:
            if component_id is cid:
                return True
        return False

    TableState.is_renameable = _is_renameable
    TableState.is_removable = _is_removable


# ---------------------------------------------------------------------------
# Patch TableViewer — registers renameable/removable callbacks (once only).
# ---------------------------------------------------------------------------

if not hasattr(TableViewer, '_shim_patched'):
    _orig_viewer_init = TableViewer.__init__

    def _patched_viewer_init(self, session, state=None):
        _orig_viewer_init(self, session, state=state)
        self.state.add_callback('renameable_components', self._update_renameable)
        self.state.add_callback('removable_components', self._update_removable)

    def _update_renameable(self, *args):
        self.widget_table._update_columns()

    def _update_removable(self, *args):
        self.widget_table._update_columns()

    TableViewer.__init__ = _patched_viewer_init
    TableViewer._update_renameable = _update_renameable
    TableViewer._update_removable = _update_removable
    TableViewer._shim_patched = True


# ---------------------------------------------------------------------------
# JdavizTableGlueShim — TableGlue subclass with new template + methods.
# ---------------------------------------------------------------------------

class JdavizTableGlue(TableGlue):
    """Temporary TableGlue subclass bundling pending glue-jupyter changes."""

    template_file = (__file__, 'table_viewer.vue')

    def _get_headers(self):
        if self.data is None:
            return []
        components = self.get_visible_components()
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


__all__ = ['JdavizTableGlue']
