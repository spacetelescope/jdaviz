import os

import ipyvuetify as v
from traitlets import Unicode, Any, List

from ..core.events import AddViewerMessage, ViewerSelectedMessage
from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tab_area.vue")) as f:
    TEMPLATE = f.read()


class TabArea(TemplateMixin):
    """
    Controls the creation of individual tabs to hold rendered glupyter viewers.

    Attributes
    ----------
    template : `Unicode`
        The file containing the vue template for rendering the component.
    tab : `Any`
        The vue model reference to the currently rendered tab component.
    active_viewers : `List`
        List of viewers currently rendered within tab components.

    Notes
    -----
    The components dictionary for this ~`ipyvuetify.VuetifyTemplate` subclass
    is populated at creation time of the application by querying the related
    registry class.
    """
    template = Unicode(TEMPLATE).tag(sync=True)
    tab = Any(None).tag(sync=True)
    active_viewers = List([]).tag(sync=True)

    def __init__(self, area=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store the area key for this tab area
        self._area = area

        # Setup up "holders" due to the fact that ipyvuetify does not support
        # dynamically adding components after the application has been rendered
        self.components = {'g-tab-{}'.format(i): v.Card(flat=True,
                                                        class_="fill-height")
                           for i in range(10)}

        # Subscribed to the add viewer messages to trigger the creation of new
        # tabs in the tab area.
        self.hub.subscribe(self, AddViewerMessage, handler=self._add_viewer)

        # When a new viewer tab is selected, fire an event
        self.observe(self._on_active_viewer_changed, names='tab')

        # Store the raw viewer object somewhere so we can still reference its
        # layout pieces
        self._viewers = {}

    def _add_viewer(self, msg):
        if not (msg.area is None or msg.area == self._area):
            return

        # Construct a reference to ipywidet parent stored in the components
        comp_ref = 'g-tab-{}'.format(len(self.active_viewers))

        # Store the name displayed in the tab bar and the binding reference
        new_viewer = {'name': 'New Viewer',
                      'binding': comp_ref}

        # Add the viewer to the active viewers filter to be iterated over in
        # the frontend
        self.active_viewers = self.active_viewers + [new_viewer]

        # Add the figure widget (plot widget) as a child to the "holder"
        msg.viewer.figure_widget.layout.width = 'auto'
        msg.viewer.figure_widget.layout.height = 'calc(100vh - 110px)'
        self.components.get(comp_ref).children = [msg.viewer.figure_widget]

        # Store the raw viewer instance
        self._viewers[comp_ref] = msg.viewer

    def _on_active_viewer_changed(self, *args):
        viewer = self._viewers.get("g-{}".format(self.tab))

        viewer_selected_message = ViewerSelectedMessage(viewer, sender=self)
        self.hub.broadcast(viewer_selected_message)

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass


class ViewerTab(v.Card):
    # template = Unicode("""
    # <v-card flat>
    #     <component v-bind:is="viewer"></component>
    # </v-card>
    # """)
    name = Unicode("").tag(sync=True)

    def __init__(self, figure, *args, **kwargs):
        super().__init__(*args, flat=True, **kwargs)

        # self.components = {'viewer': figure}


