import os

from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.message import EditSubsetMessage
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.widgets.subset_select_vuetify import SubsetSelect
from traitlets import Any, Bool, Dict, Int, List, Unicode

from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['ViewerOptions']

with open(os.path.join(os.path.dirname(__file__), "viewer_options.vue")) as f:
    TEMPLATE = f.read()


class ViewerOptions(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
