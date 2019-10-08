import os

from traitlets import Unicode, Any, Dict, List

from ..core.template_mixin import TemplateMixin
from ..core.events import AddViewerMessage

import ipyvuetify as v

with open(os.path.join(os.path.dirname(__file__), "tab_area.vue")) as f:
        TEMPLATE = f.read()


class TabArea(TemplateMixin):
    tab = Any(None).tag(sync=True)
    template = Unicode(TEMPLATE).tag(sync=True)
    viewers = List([]).tag(sync=True)
    text = Unicode("Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                   "sed do eiusmod tempor incididunt ut labore et dolore magna "
                   "aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
                   "ullamco laboris nisi ut aliquip ex ea commodo consequat.").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {'g-tab-{}'.format(i):
                               v.Card(flat=True, children=['TESTING {}'.format(i)])
                           for i in range(10)}

        self.hub.subscribe(self, AddViewerMessage, handler=self._add_viewer)

    def _add_viewer(self, msg):
        new_viewer = {'name': 'New Viewer',
                      'child': msg.viewer,
                      'binding': 'g-tab-{}'.format()}
