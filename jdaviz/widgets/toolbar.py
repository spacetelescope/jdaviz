import os

from traitlets import Unicode, List, Int

from ..core.template_mixin import TemplateMixin

__all__ = ['Toolbar']

with open(os.path.join(os.path.dirname(__file__), "toolbar.vue")) as f:
    TEMPLATE = f.read()


class Toolbar(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    tool_names = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_tool(self, name):
        self.tool_names.append(name)

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass
