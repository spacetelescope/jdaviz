import os

from traitlets import Unicode, Int

from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tab_area.vue")) as f:
        TEMPLATE = f.read()


class TabArea(TemplateMixin):
    tab = Int(0).tag(sync=True)
    template = Unicode(TEMPLATE).tag(sync=True)
    text = Unicode("Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                   "sed do eiusmod tempor incididunt ut labore et dolore magna "
                   "aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
                   "ullamco laboris nisi ut aliquip ex ea commodo consequat.").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
