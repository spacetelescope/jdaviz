import os

import ipyvuetify as v
from traitlets import Unicode, Any, List

from ..core.events import AddViewerMessage
from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tab_area.vue")) as f:
        TEMPLATE = f.read()


class TabArea(TemplateMixin):
    tab = Any(None).tag(sync=True)
    template = Unicode(TEMPLATE).tag(sync=True)
    active_viewers = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Setup up "holders" due to the fact that ipyvuetify does not support
        # dynamically adding components after the application has been rendered
        self.components = {'g-tab-{}'.format(i): v.Card(flat=True)
                           for i in range(10)}

        # Subscribed to the add viewer messages to trigger the creation of new
        # tabs in the tab area.
        self.hub.subscribe(self, AddViewerMessage, handler=self._add_viewer)

    def _add_viewer(self, msg):
        # Construct a reference to ipywidet parent stored in the components
        comp_ref = 'g-tab-{}'.format(len(self.active_viewers))

        # Store the name displayed in the tab bar and the binding reference
        new_viewer = {'name': 'New Viewer',
                      'binding': comp_ref}

        # Add the viewer to the active viewers filter to be iterated over in
        # the frontend
        self.active_viewers = self.active_viewers + [new_viewer]

        # Add the figure widget (plot widget) as a child to the "holder"
        self.components.get(comp_ref).children = [msg.viewer.figure_widget]

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass
