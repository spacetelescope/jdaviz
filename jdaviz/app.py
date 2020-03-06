import os

import ipyvuetify as v
import ipywidgets as w
import pkg_resources
import yaml
from glue_jupyter.app import JupyterApplication
from glue.core.message import DataCollectionAddMessage
from ipysplitpanes import SplitPanes
from ipyvuedraggable import Draggable
from traitlets import Unicode, Bool, Dict, List, Int, observe
import uuid
import numpy as np

from .components import ViewerArea, TrayArea
from .core.events import AddViewerMessage, NewViewerMessage, LoadDataMessage
from .core.registries import tool_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

SplitPanes()
Draggable()


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

    show_component = Dict({
        'menu_bar': True,
        'toolbar': True,
        'tray_area': True
    }).tag(sync=True)

    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_tray_bar = Bool(False).tag(sync=True)

    selected_viewer_item = Dict({}).tag(sync=True)
    selected_stack_item_id = Unicode().tag(sync=True) #Dict({}).tag(sync=True)
    data_items = List([]).tag(sync=True)
    tool_items = List([]).tag(sync=True, **w.widget_serialization)
    stack_items = List([
        # {
        #     'id': str(uuid.uuid4()),
        #     'tab': 0,
        #     'viewers': [
        #         {
        #             'id': str(uuid.uuid4()),
        #             'type': 'gl-stack',
        #             'children': [],
        #             'widget': w.IntSlider(value=10),
        #             'name': "Slider Test",
        #             'fab': False,
        #             'tools': None,
        #             'layer_options': None,
        #             'viewer_options': None,
        #             'drawer': False,
        #             'selected_data_items': []
        #         }
        #     ]
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
    css = load_template("app.css", __file__).tag(sync=True)

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

        # Subscribe to the event fired when data is added to the application-
        # level data collection object
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        return self._application_handler.session

    def load_data(self, path):
        self._application_handler.load_data(path)

    @observe('stack_items')
    def vue_relayout(self, *args, **kwargs):
        for stack in self.stack_items:
            for viewer in stack.get('viewers'):
                viewer.get('widget').layout.height = '99.9%'
                viewer.get('widget').layout.height = '100%'

    def _on_data_added(self, msg):
        self.data_items = self.data_items + [
            {
                'id': str(uuid.uuid4()),
                'name': msg.data.label,
                'locked': True,#not bool(self.selected_viewer_item),
                'children': [
                    # {'id': 2, 'name': 'Calendar : app'},
                    # {'id': 3, 'name': 'Chrome : app'},
                    # {'id': 4, 'name': 'Webstorm : app'},
                ],
            }
        ]

    @observe('selected_viewer_item')
    def _on_viewer_selected(self, event):
        if event['old'].get('id') == event['new'].get('id'):
            return

        tmp_data_items = self.data_items
        self.data_items = []

        for item in tmp_data_items:
            item['locked'] = not bool(self.selected_viewer_item)

        self.data_items = tmp_data_items

        # if True:
        #     new_dict = {}
        #     new_dict.update(self.data_items)

        #     self.data_items = new_dict

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        self.hub.broadcast(AddViewerMessage(view, sender=self))

        selection_tools = view.toolbar_selection_tools
        selection_tools.borderless = True
        selection_tools.tile = True

        # Add viewer locally
        self.stack_items = self.stack_items + [
            {
                'id': str(uuid.uuid4()),
                'tab': 0,
                'active': False,
                'viewers':
                [
                    {
                        'id': str(uuid.uuid4()),
                        'type': 'gl-stack',
                        'children': [],
                        'widget': view.figure_widget,
                        'name': "Slider Test",
                        'fab': False,
                        'tools': selection_tools,
                        'layer_options': view.layer_options,
                        'viewer_options': view.viewer_options,
                        'drawer': False,
                        'selected_data_items': []
                    }
                ]
            }
        ]

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
            self.tool_items = self.tool_items + [{
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
