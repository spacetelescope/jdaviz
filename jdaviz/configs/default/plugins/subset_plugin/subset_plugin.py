from glue.core.message import EditSubsetMessage, SubsetCreateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from traitlets import List, Unicode, Bool, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, SubsetSelect

__all__ = ['SubsetPlugin']

SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


@tray_registry('g-subset-plugin', label="Subset Tools")
class SubsetPlugin(TemplateMixin):
    template_file = __file__, "subset_plugin.vue"
    select = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("No selection (create new)").tag(sync=True)
    mode_selected = Unicode('add').tag(sync=True)
    show_region_info = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.session.hub.subscribe(self, EditSubsetMessage,
                                   handler=self._sync_selected_from_state)
        self.session.hub.subscribe(self, SubsetCreateMessage,
                                   handler=self._sync_available_from_state)

        self.no_selection_text = "No selection (create new)"
        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          default_text=self.no_selection_text)

    def _sync_selected_from_state(self, *args):
        if self.session.edit_subset_mode.edit_subset == []:
            if self.subset_selected != self.no_selection_text:
                self.subset_selected = self.no_selection_text
                self.show_region_info = False
        else:
            new_label = self.session.edit_subset_mode.edit_subset[0].label
            if new_label != self.subset_selected:
                self.subset_selected = self.session.edit_subset_mode.edit_subset[0].label
                self.show_region_info = True
                self._get_region_definition()

    def _sync_available_from_state(self, *args):
        self.subset_items = [{'label': self.no_selection_text}] + [
                             self.subset_select._subset_to_dict(subset) for subset in
                             self.data_collection.subset_groups]

    @observe('subset_selected')
    def _sync_selected_from_ui(self, change):
        self.show_region_info = change['new'] != self.no_selection_text
        m = [s for s in self.app.data_collection.subset_groups if s.label == change['new']]
        self.session.edit_subset_mode.edit_subset = m

    '''
    # This will be needed once we use a dropdown instead of the actual
    # g-subset-mode component
    @observe("mode_selected")
    def _mode_selected_changed(self, event={}):
        if self.session.edit_subset_mode != self.mode_selected:
            self.session.edit_subset_mode = self.mode_selected
    '''

    def _get_region_definition(self):

        pass
