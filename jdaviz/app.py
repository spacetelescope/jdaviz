import os

import ipyvuetify as v
import yaml
from glue.core.application_base import HubListener
from glue_jupyter.app import JupyterApplication
from traitlets import Unicode, Bool, Dict, observe

from jdaviz.core.registries import tools, trays, viewers
from .core.events import NewViewerMessage, AddViewerMessage, LoadDataMessage
from .widgets.content_area import ContentArea
from .widgets.menu_bar import MenuBar
from .widgets.toolbar import Toolbar
from .widgets.tray_bar import TrayBar

with open(os.path.join(os.path.dirname(__file__), "app.vue")) as f:
    TEMPLATE = f.read()


class IPyApplication(v.VuetifyTemplate, HubListener):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_tray_bar = Bool(True).tag(sync=True)
    notebook_context = Bool(False).tag(sync=True)
    drawer = Bool(False).tag(sync=True)
    source = Unicode("").tag(sync=True)

    template = Unicode(TEMPLATE).tag(sync=True)

    methods = Unicode("""
    {
        checkNotebookContext() {
            this.notebook_context = !!!document.getElementById("web-app");
            return this.notebook_context;
        }
    }
    """).tag(sync=True)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: we shouldn't need to keep an entire JupyterApplication
        #  instance, however, there are certain things on the glupyter viewers
        #  that reference custom functionality in this class. Eventually, we
        #  should parse those out so they aren't dependencies.
        self._application_handler = JupyterApplication()

        # Instantiate the default gui components
        self.components = {
            'g-toolbar': Toolbar(session=self.session),
            'g-tray-bar': TrayBar(session=self.session),
            'g-content-area': ContentArea(session=self.session),
            'g-menu-bar': MenuBar(session=self.session)
        }

        # Dump all user-defined toolbar items as component references in the
        #  vuetify template instance.
        toolbar = self.components.get('g-toolbar')

        toolbar.components = {k: v(session=self.session)
                              for k, v in tools.members.items()}

        # Do the same thing for the sidebar components
        tray_bar = self.components.get('g-tray-bar')

        tray_bar.components = {k: v.get('cls')(session=self.session)
                               for k, v in trays.members.items()}

        # Load in default configuration file
        self.load_configuration(configuration)

        # Setup hub event listeners
        self.hub.subscribe(self, NewViewerMessage,
                           handler=self._on_new_viewer)
        self.hub.subscribe(self, LoadDataMessage,
                           handler=self._on_load_data)

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        return self._application_handler.session

    @observe('notebook_context')
    def _on_context_changed(self, event):
        """
        Observe changes in the rendered context of the application. If the
        application is viewed inside a notebook, disable the app props on the
        vuetify components.

        Parameters
        ----------
        event : dict
            Contains the trailet event properties.
        """
        self.components.get('g-toolbar').app = not event['new']
        self.components.get('g-tray-bar').app = not event['new']

    def load_configuration(self, path):
        # Parse the default configuration file
        default_path = os.path.join(os.path.dirname(__file__), "configs")

        if path is None or path == 'default':
            path = os.path.join(default_path, "default", "default.yaml")
        elif path == 'cubeviz':
            path = os.path.join(default_path, "cubeviz", "cubeviz.yaml")
        elif not os.path.isfile(path):
            raise ValueError("Configuration must be path to a .yaml file.")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # Get a reference to the component visibility states
        comps = config.get('components', {})

        # Toggle the rendering of the components in the gui
        self.show_menu_bar = comps.get('menu_bar', True)
        self.show_toolbar = comps.get('toolbar', True)
        self.show_tray_bar = comps.get('tray_bar', True)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            self.components['g-toolbar'].add_tool(name)

        # Add the tray items filter to the interact drawer component
        for name in config.get('tray_bar', []):
            # Retrieve the meta information around the rendering of the tab
            #  button including the icon and label information.
            item = trays.members.get(name)

            label = item.get('label')
            icon = item.get('icon')

            self.components['g-tray-bar'].add_tray(name, label, icon)

        # Pre-load viewers into tab area
        content_area = config.get('content_area')

        # Toggle the visibility of the tab areas with the content area.
        # TODO: this will changed when ipygoldenlayout is properly
        #   implemented.
        if content_area is not None:
            self.components['g-content-area'].bottom_area = 'bottom_area' in content_area

            for area in content_area:
                for viewer_label in content_area.get(area):
                    viewer = viewers.members.get(viewer_label)

                    if viewer is not None:
                        viewer_cls = viewer.get('cls')

                        view = self._application_handler.new_data_viewer(
                            viewer_cls, data=None, show=False)

                        # Give the viewers a reference to the hub.
                        # TODO: this is a hack, do we really want to have
                        #  viewers listening to events?
                        if hasattr(view, 'setup_hub'):
                            view.setup_hub(self.hub)

                        self.hub.broadcast(
                            AddViewerMessage(view, area=area, sender=self))

    def _on_load_data(self, msg):
        data = self._application_handler.load_data(msg.path)

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        self.hub.broadcast(AddViewerMessage(view, sender=self))

        return view
