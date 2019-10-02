import os

from traitlets import Unicode
from ipywidgets import IntSlider, VBox

from glue_jupyter.baldr.core.events import NewProfile1DMessage
from glue_jupyter.baldr.core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tab_area.vue")) as f:
        TEMPLATE = f.read()


class TabArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, NewProfile1DMessage, handler=self.vue_add_child)

    def vue_add_child(self, msg):

        self._golden_layout.children = [
            VBox([msg.figure.toolbar_selection_tools,
                  msg.figure.figure_widget])]
