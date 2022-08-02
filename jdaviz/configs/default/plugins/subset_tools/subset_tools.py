from glue.core.message import EditSubsetMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.widgets.subset_select_vuetify import SubsetSelect
from traitlets import Int, List

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['SubsetTools']

SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


@tool_registry('g-subset-tools')
class SubsetTools(TemplateMixin):
    template_file = __file__, "subset_tools.vue"
    select = List([]).tag(sync=True)
    subset_mode = Int(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-select': SubsetSelect(session=self.session),
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.hub.subscribe(self, EditSubsetMessage,
                           handler=self._subset_edit_event)

    def _subset_edit_event(self, msg):
        # NOTE: here we'll assume that only a single subset is selected (glue supports
        # multiple subsets being selected, but jdaviz doesn't)
        if not (len(msg.subset)):
            # then changed to "Create New", we want to revert the mode to ReplaceMode
            self.session.edit_subset_mode.mode = ReplaceMode
