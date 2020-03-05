import os

import ipyvuetify as v
import ipywidgets as w
import pkg_resources
import yaml
from glue_jupyter.app import JupyterApplication
from ipygoldenlayout import GoldenLayout
from traitlets import Unicode, Bool, Dict, List, Int

from .components import ViewerArea, TrayArea
from .core.events import AddViewerMessage, NewViewerMessage, LoadDataMessage
from .core.registries import tool_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

GoldenLayout()


class ViewCell(v.VuetifyTemplate):
    template = Unicode("""
    <component
        v-bind:is="comp_name"
        v-bind:key="index">
    </component>
    """).tag(sync=True)

    comp_name = Unicode("").tag(sync=True)
    index = Int(0).tag(sync=True)


class Application(TemplateMixin):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    drawer = Bool(True).tag(sync=True)

    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_tray_bar = Bool(False).tag(sync=True)

    tools = List([]).tag(sync=True, **w.widget_serialization)
    viewer_layout = List([
        # {
        #     'type': 'gl-stack',
        #     'children': [],
        #     'widget': w.IntSlider(value=10),
        #     'name': "Slider Test",
        #     'fab': False
        # }
    ]).tag(sync=True, **w.widget_serialization)

    template = load_template("app.vue", __file__).tag(sync=True)
    methods = Unicode("""
    {
        checkNotebookContext() {
            this.notebook_context = document.getElementById("ipython-main-app");
            return this.notebook_context;
        },

        loadRemoteCSS() {
            window.addEventListener("resize", function() {
                console.log("RESIZING");
            });
            var muiIconsSheet = document.createElement("link");
            muiIconsSheet.type = "text/css";
            muiIconsSheet.rel = "stylesheet";
            muiIconsSheet.href =
                "https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css";
            document.getElementsByTagName("head")[0].appendChild(muiIconsSheet);
            return true;
        }
    }
    """).tag(sync=True)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._application_handler = JupyterApplication()

        # Load in default configuration file. This must come before loading
        #  in the components for the toolbar/tray_bar.
        # self.load_configuration(configuration)

        plugins = {
            entry_point.name: entry_point.load()
            for entry_point
            in pkg_resources.iter_entry_points(group='plugins')}

        components = {
            'g-viewer-area': ViewerArea(session=self.session),
            'g-tray-area': TrayArea(session=self.session)}

        components.update({k: v(session=self.session)
                           for k, v in tool_registry.members.items()})

        self.components = components

        # Parse configuration
        self.load_configuration(configuration)

        # Subscribe to viewer messages
        self.hub.subscribe(self, NewViewerMessage,
                           handler=self._on_new_viewer)

        # Subscribe to load data messages
        self.hub.subscribe(self, LoadDataMessage,
                           handler=lambda msg: self.load_data(msg.path))

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        return self._application_handler.session

    def load_data(self, path):
        self._application_handler.load_data(path)

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        self.hub.broadcast(AddViewerMessage(view, sender=self))

        # Add viewer locally
        self.viewer_layout = self.viewer_layout + [{
            'type': 'gl-stack',
            'children': [],
            'widget': view.figure_widget,
            'name': "Slider Test",
            'fab': False
        }]

        return view

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
        # comps = config.get('components', {})

        # Toggle the rendering of the components in the gui
        # self.show_menu_bar = comps.get('menu_bar', True)
        # self.show_toolbar = comps.get('toolbar', True)
        # self.show_tray_bar = comps.get('tray_bar', True)

        # if 'viewer_area' in config:
        #     viewer_area_layout = config.get('viewer_area')
        #     self.components.get('g-viewer-area').parse_layout(viewer_area_layout)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(session=self.session)
            self.tools = self.tools + [{
                'name': name,
                'widget': tool
            }]

        # Add the tray items filter to the interact drawer component
        # for name in config.get('tray_bar', []):
        #     # Retrieve the meta information around the rendering of the tab
        #     #  button including the icon and label information.
        #     item = trays.members.get(name)

        #     label = item.get('label')
        #     icon = item.get('icon')

        #     self.components['g-tray-bar'].add_tray(name, label, icon)
