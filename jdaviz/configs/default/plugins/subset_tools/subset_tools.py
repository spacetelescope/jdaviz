import os

import ipywidgets as w
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.message import EditSubsetMessage
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.widgets.subset_select_vuetify import SubsetSelect
from traitlets import Int, List, Unicode

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

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
    template = load_template("subset_tools.vue", __file__).tag(sync=True)
    select = List([]).tag(sync=True)
    subset_mode = Int(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-select': SubsetSelect(session=self.session),
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        # self.hub.subscribe(self, EditSubsetMessage,
        #                    handler=self.vue_subset_mode_changed)

    # def vue_subset_mode_changed(self, index):
    #     mode = list(SUBSET_MODES.values())[index]

    #     if self.session.edit_subset_mode.mode != mode:
    #         self.session.edit_subset_mode.mode = mode
