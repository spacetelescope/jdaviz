from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.widgets.subset_select_vuetify import SubsetSelect
from traitlets import Int, List, Unicode, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, SubsetSelect as JSubsetSelect

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
    template_file = __file__, "subset_tools.vue"
    select = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    subset_selected = List([]).tag(sync=True)
    mode_selected = Unicode('add').tag(sync=True)
    subset_selected_plugin = Unicode('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-select': SubsetSelect(session=self.session),
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.subset_items = self.components['g-subset-select'].available
        self.subset_selected = self.components['g-subset-select'].selected
        no_selection_text = self.components['g-subset-select'].no_selection_text

        self.subset_select = JSubsetSelect(self,
                                           'subset_items',
                                           'subset_selected_plugin',
                                           default_text=no_selection_text)


    @observe("subset_selected")
    def _subset_selected_changed(self, event={}):
        if isinstance(self.subset_selected, list):
            self.subset_selected_plugin = self.subset_selected[0]
        else:
            raise ValueError(f"Got non-list subset selection: {self.subset_selected} "
                             f"{type(self.subset_selected)}")

    @observe("mode_selected")
    def _mode_selected_changed(self, event={}):
        if self.session.edit_subset_mode != mode_selected:
            self.session.edit_subset_mode = mode_selected
