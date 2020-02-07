import os

import ipywidgets as w
from glue.core.edit_subset_mode import OrMode, AndNotMode, AndMode, XorMode, \
    ReplaceMode
from glue.core.message import EditSubsetMessage
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.widgets.subset_select_vuetify import SubsetSelect
from traitlets import Unicode, List, Int

from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['DefaultToolbar']

with open(os.path.join(os.path.dirname(__file__), "toolbar.vue")) as f:
    TEMPLATE = f.read()

SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


class DefaultToolbar(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    tools = List([]).tag(sync=True, **w.widget_serialization)
    select = List([]).tag(sync=True)
    subset_mode = Int(0).tag(sync=True)

    items = List([
        {
            'icon': 'mdi-plus',
            'text': 'Create New'
        }
    ]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-select': SubsetSelect(session=self.session),
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.hub.subscribe(self, EditSubsetMessage,
                           handler=self.vue_subset_mode_changed)

    def vue_subset_mode_changed(self, index):
        mode = list(SUBSET_MODES.values())[index]

        if self.session.edit_subset_mode.mode != mode:
            self.session.edit_subset_mode.mode = mode

    def add_tool(self, tool):
        self.tools = self.tools + [tool]
