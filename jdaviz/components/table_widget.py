# Jdaviz additions to glue_jupyter.table.viewer.TableGlue:
# inline column-header rename/delete traitlets and vue_* handlers.
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

    # Set by vue_rename_colum when the user accepts a rename.
    # Observed by JdavizTableViewer._on_header_renamed.
    header_renamed = traitlets.Dict({'column': '', 'newName': ''}).tag(sync=True)

    # Set by vue_remove_column when the user confirms a deletion.
    # Observed by JdavizTableViewer._on_header_deleted.
    header_deleted = traitlets.Unicode('').tag(sync=True)

    # Column names whose pencil/delete icons should be hidden (role columns).
    non_removable_headers = traitlets.List([]).tag(sync=True)

    # Python → Vue: set to a column name to trigger Vue rename mode immediately
    # (used after programmatically adding a column so the user can name it).
    header_enter_edit_mode = traitlets.Unicode('').tag(sync=True)

    # ---- vue_* handlers (called from the Vue frontend) ----

    def vue_rename_colum(self, data):
        """User accepted a column rename in the header text-input.

        Directly renames the component in the current glue Data object, then
        sets ``header_renamed`` so external observers (e.g. the viewer's
        role-label bookkeeping) can react.
        """
        old_name = data.get('column', '')
        new_name = data.get('newName', '').strip()
        if not old_name or not new_name or old_name == new_name:
            return
        if self.data is not None and old_name in [c.label for c in self.data.main_components]:
            self.data.id[old_name].label = new_name
            self._update_columns()
        self.header_renamed = {'column': old_name, 'newName': new_name}

    def vue_remove_column(self, data):
        """User confirmed a column deletion via the remove-confirm badge.

        Directly removes the component from the current glue Data object, then
        sets ``header_deleted`` so external observers can react.
        """
        label = data.get('column', '')
        if not label or self.data is None:
            return
        if label in [c.label for c in self.data.main_components]:
            cid = self.data.id[label]
            self.state.editable_components = [
                c for c in self.state.editable_components if c is not cid
            ]
            self.data.remove_component(cid)
            self._update()
        self.header_deleted = label
