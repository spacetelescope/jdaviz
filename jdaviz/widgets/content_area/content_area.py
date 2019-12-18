import os

from traitlets import Unicode, Bool, List
import ipyvuetify as v

from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import AddViewerMessage, ViewerSelectedMessage
from ipygoldenlayout import GoldenLayout

with open(os.path.join(os.path.dirname(__file__), "content_area.vue")) as f:
    TEMPLATE = f.read()


class ContentArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    active_viewers = List([]).tag(sync=True)

    css = Unicode("""
    .container.fill-height {
        flex-wrap: wrap;
    }

    .container.fill-height > .row {
        flex: 1 1 100%;
    }
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Necessary to load in configurations for golden layout
        GoldenLayout()

        self._viewers = {}

        # Setup up "holders" due to the fact that ipyvuetify does not support
        # dynamically adding components after the application has been rendered
        self.components = {'g-tab-{}'.format(i): v.Card(flat=True,
                                                        class_="fill-height")
                           for i in range(100)}

        # Subscribed to the add viewer messages to trigger the creation of new
        # tabs in the tab area.
        self.hub.subscribe(self, AddViewerMessage, handler=self._add_viewer)

        # When a new viewer tab is selected, fire an event
        self.observe(self._on_active_viewer_changed, names='tab')

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
        msg.viewer.figure_widget.layout.width = '100%'
        msg.viewer.figure_widget.layout.height = '100%'#''calc(100vh - 110px)'
        self.components.get(comp_ref).children = [msg.viewer.figure_widget]

        # Store the raw viewer instance
        self._viewers[comp_ref] = msg.viewer

    def _on_active_viewer_changed(self):
        pass

    def vue_on_component_resized(self, event):
        import random

        for comp_ref, viewer in self._viewers.items():
            comp = self.components.get(comp_ref)
            print(viewer.figure_widget.layout)
            viewer.figure_widget.layout.width = 'calc(100vh)' #''{}px'.format(random.randint(100, 500))
            viewer.figure_widget.layout.height = 'calc(100vh)' #'{}px'.format(random.randint(100, 500))


class TabbedViewer(TemplateMixin):
    template = Unicode("""
    <template>
        <v-card>
            <g-viewer-toolbar />
            <g-viewer />
        </v-card>
    </template>
    """).tag(sync=True)

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {'g-viewer-toolbar': viewer.toolbar_selection_tools,
                           'g-viewer': viewer.figure_widget}
