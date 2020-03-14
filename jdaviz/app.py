import os

import ipyvuetify as v
import ipywidgets as w
import pkg_resources
import yaml
from glue_jupyter.app import JupyterApplication
from glue.core.message import DataCollectionAddMessage
from glue.core import BaseData
from ipysplitpanes import SplitPanes
from ipyvuedraggable import Draggable
from ipygoldenlayout import GoldenLayout
from traitlets import Unicode, Bool, Dict, List, Int, observe, ObjectName
import uuid
import numpy as np

from .core.events import AddViewerMessage, NewViewerMessage, LoadDataMessage
from .core.registries import tool_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

SplitPanes()
Draggable()
GoldenLayout()

class Application(TemplateMixin):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    drawer = Bool(True).tag(sync=True)

    settings = Dict({
        'show_component': {
            'menu_bar': True,
            'toolbar': True,
            'tray_area': True
        },
        'show_tab_headers': True,
        'context': {
                'notebook': {
                    'max-height': '500px'
                }
            }
    }).tag(sync=True)

    selected_viewer_item = Dict({}).tag(sync=True, **w.widget_serialization)
    selected_stack_item = Dict({}).tag(sync=True, **w.widget_serialization)
    selected_data_items = List([]).tag(sync=True)

    data_items = List([]).tag(sync=True)
    tool_items = List([]).tag(sync=True, **w.widget_serialization)
    stack_items = List([]).tag(sync=True, **w.widget_serialization)

    template = load_template("app.vue", __file__).tag(sync=True)

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

        components = {k: v(session=self.session)
                      for k, v in tool_registry.members.items()}

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

        # Create a dictionary for holding non-ipywidget viewer objects
        self._base_viewers = {}

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        return self._application_handler.session

    @property
    def data_collection(self):
        return self._application_handler.data_collection

    def load_data(self, path):
        self._application_handler.load_data(path)

    @observe('stack_items')
    def vue_relayout(self, *args, **kwargs):
        for stack in self.stack_items:
            for viewer in stack.get('viewers'):
                viewer.get('widget').layout.height = '99.9%'
                viewer.get('widget').layout.height = '100%'

    @observe('selected_viewer_item')
    def _on_viewer_item_selected(self, event):
        selected_viewer_id = self.selected_viewer_item['id']
        selected_viewer = self._viewer_by_id(selected_viewer_id)
        self.selected_data_items = selected_viewer['selected_data_items']

    @observe('selected_data_items')
    def _on_data_item_selected(self, event):
        selected_viewer_id = self.selected_viewer_item['id']
        selected_viewer = self._viewer_by_id(selected_viewer_id)
        selected_viewer['selected_data_items'] = event['new']

    def vue_data_item_selected(self, data_ids, **kwargs):
        # data_ids = event['new'].get(self.selected_viewer_item_id, [])

        # Find the active viewer
        active_viewer_id = self.selected_viewer_item['id']
        active_viewer = self._base_viewers.get(active_viewer_id)

        active_data_labels = []

        # Include any selected data in the viewer
        for data_id in data_ids:
            [label] = [x['name'] for x in self.data_items if x['id'] == data_id]
            active_data_labels.append(label)

            [data] = [x for x in self.data_collection if x.label == label]

            active_viewer.add_data(data)

        # Remove any deselected data objects from viewer
        viewer_data = [layer_state.layer for layer_state in active_viewer.state.layers
                       if hasattr(layer_state, 'layer') and isinstance(layer_state.layer, BaseData)]

        for data in viewer_data:
            if data.label not in active_data_labels:
                active_viewer.remove_data(data)

    def vue_remove_viewer(self, *args):
        viewer_id, stack_id = args[0]
        viewer_item = self._viewer_by_id(viewer_id, stack_id)

        temp_stack_items = self.stack_items

        for stack in temp_stack_items:
            if stack['id'] == stack_id:
                stack['viewers'].remove(viewer_item)
                break

        self.stack_items = []
        self.stack_items = temp_stack_items

    @observe('stack_items')
    def _on_stack_items_changed(self, event):
        new_stack_items = [x for x in self.stack_items]

        for stack in self.stack_items:
            if len(stack['viewers']) == 0:
                new_stack_items.remove(stack)

        self.stack_items = new_stack_items

    def _stack_by_id(self, stack_id):
        return next((stack for stack in self.stack_items
                     if stack['id'] == stack_id), {})

    def _viewer_by_id(self, viewer_id, stack_id=None):
        if stack_id is None:
            stack_id = self.selected_stack_item.get('id')

        [stack_item] = [x for x in self.stack_items
                        if x['id'] == stack_id]

        return next((viewer for viewer in stack_item.get('viewers', [])
                     if viewer['id'] == viewer_id), {})

    def _on_data_added(self, msg):
        self.data_items = self.data_items + [
            {
                'id': str(uuid.uuid4()),
                'name': msg.data.label,
                'locked': False, # not bool(self.selected_viewer_item),
                'children': [
                    # {'id': 2, 'name': 'Calendar : app'},
                    # {'id': 3, 'name': 'Chrome : app'},
                    # {'id': 4, 'name': 'Webstorm : app'},
                ],
            }
        ]

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        selection_tools = view.toolbar_selection_tools.children

        for tool in selection_tools:
            btn = tool.v_slots[0].get('children')
        #     btn.color = 'blue darken-2'
            btn.icon = False
        #     btn.fab = True
        #     btn.background_color = "white"
        #     btn.dark = False
        #     btn.outlined = True
        #     btn.small = True
        #     btn.class_ = "elevation-0"

        # selection_tools.borderless = True
        # selection_tools.tile = True

        # Create the viewer item dictionary
        new_viewer_item = {
            'id': str(uuid.uuid4()),
            'component': 'gl-row',
            'children': [],
            'widget': view.figure_widget,
            'name': "Slider Test",
            'fab': False,
            'tools': selection_tools,
            'layer_options': view.layer_options,
            'viewer_options': view.viewer_options,
            'selected': False,
            'selected_data_items': []
        }

        new_stack_item = {
            'id': str(uuid.uuid4()),
            'tab': 0,
            'active': False,
            'viewers': [
                new_viewer_item
            ]
        }

        # Add viewer locally
        self.stack_items = self.stack_items + [
            new_stack_item
        ]

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        self._base_viewers[new_viewer_item['id']] = view

        # Make this view the active viewer
        self.selected_stack_item = new_stack_item
        self.selected_viewer_item = new_viewer_item

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
