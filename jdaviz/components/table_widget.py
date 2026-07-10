import traitlets
from glue_jupyter.table.viewer import TableGlue

__all__ = ['JdavizTableWidget']


class JdavizTableWidget(TableGlue):
    """TableGlue subclass that adds inline column-header rename/delete UX.

    All business logic (traitlets + vue_* handlers) lives here so that
    glue-jupyter only needs the minimal ``_widget_table_cls`` hook.
    """

    template_file = (__file__, 'table_widget.vue')

    # ---- inline column-header editing traitlets ----

    # Set by vue_commit_header_edit when the user accepts a rename.
    # Observed by JdavizTableViewer._on_header_renamed.
    header_renamed = traitlets.Dict({'column': '', 'newName': ''}).tag(sync=True)

    # Set by vue_delete_header when the user confirms a deletion.
    # Observed by JdavizTableViewer._on_header_deleted.
    header_deleted = traitlets.Unicode('').tag(sync=True)

    # Column names whose pencil/delete icons should be hidden (role columns).
    non_removable_headers = traitlets.List([]).tag(sync=True)

    # Python → Vue: set to a column name to trigger Vue rename mode immediately
    # (used after programmatically adding a column so the user can name it).
    header_enter_edit_mode = traitlets.Unicode('').tag(sync=True)

    # ---- vue_* handlers (called from the Vue frontend) ----

    def _get_headers(self):
        """Override to add Vuetify 3 required `title` and `key` fields."""
        headers = super()._get_headers()
        for h in headers:
            # Vuetify 3 uses 'title' (not 'text') and 'key' (not 'value')
            h['title'] = h.get('text', '')
            h['key'] = h.get('value', '')
        return headers

    def vue_commit_header_edit(self, data):
        """User accepted a column rename in the header text-input."""
        self.header_renamed = {
            'column': data.get('column', ''),
            'newName': data.get('newName', ''),
        }

    def vue_delete_header(self, data):
        """User confirmed a column deletion via the remove-confirm badge."""
        self.header_deleted = data.get('column', '')
