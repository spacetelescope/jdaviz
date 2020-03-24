import os

import ipyvuetify as v
import ipywidgets as w
import pkg_resources
import yaml
from glue_jupyter.app import JupyterApplication
from glue.core.message import DataCollectionAddMessage
from glue.core import BaseData
from ipysplitpanes import SplitPanes
from ipygoldenlayout import GoldenLayout
from traitlets import Unicode, Bool, Dict, List, Int, observe, ObjectName
import uuid
import numpy as np

from .core.events import AddViewerMessage, NewViewerMessage, LoadDataMessage
from .core.registries import tool_registry, tray_registry, viewer_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

SplitPanes()
GoldenLayout()

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')


class Application(TemplateMixin):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    drawer = Bool(False).tag(sync=True)

    settings = Dict({
        'visible': {
            'menu_bar': True,
            'toolbar': True,
            'tray': True,
            'tab_headers': True,
        },
        'context': {
            'notebook': {
                'max_height': '500px'
            }
        },
        'layout': {
        }
    }).tag(sync=True)

    data_items = List([]).tag(sync=True)
    tool_items = List([]).tag(sync=True, **w.widget_serialization)
    tray_items = List([]).tag(sync=True, **w.widget_serialization)
    stack_items = List([]).tag(sync=True, **w.widget_serialization)

    template = load_template("app.vue", __file__).tag(sync=True)

    components = Dict({'g-viewer-tab': load_template(
        "container.vue", __file__, traitlet=False)}).tag(
            sync=True, **w.widget_serialization)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._application_handler = JupyterApplication()

        plugins = {
            entry_point.name: entry_point.load()
            for entry_point
            in pkg_resources.iter_entry_points(group='plugins')}

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

    def vue_on_state_changed(self, *args, **kwargs):
        print(args, kwargs)

    def load_data(self, path):
        self._application_handler.load_data(path)

    @observe('stack_items')
    def vue_relayout(self, *args, **kwargs):
        def resize(stack_items):
            for stack in stack_items:
                for viewer in stack.get('viewers'):
                    viewer.get('widget').layout.height = '99.9%'
                    viewer.get('widget').layout.height = '100%'

                if len(stack.get('children')) > 0:
                    resize(stack.get('children'))

        resize(self.stack_items)

    # @observe('stack_items')
    # def _on_stack_items_changed(self, event):
    #     new_stack_items = [x for x in self.stack_items]

    #     for stack in self.stack_items:
    #         if len(stack['viewers']) == 0:
    #             new_stack_items.remove(stack)

    #     self.stack_items = new_stack_items

    def vue_data_item_selected(self, viewer, **kwargs):
        # data_ids = event['new'].get(self.selected_viewer_item_id, [])

        # Find the active viewer
        active_viewer_id = viewer.get('id')
        active_viewer = self._base_viewers.get(active_viewer_id)

        data_ids = viewer.get('selected_data_items', [])

        active_data_labels = []

        # Include any selected data in the viewer
        for data_id in data_ids:
            [label] = [x['name']
                       for x in self.data_items if x['id'] == data_id]
            active_data_labels.append(label)

            [data] = [x for x in self.data_collection if x.label == label]

            active_viewer.add_data(data)

        # Remove any deselected data objects from viewer
        viewer_data = [layer_state.layer
                       for layer_state in active_viewer.state.layers
                       if hasattr(layer_state, 'layer') and
                       isinstance(layer_state.layer, BaseData)]

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

    def vue_on_selected_tab_changed(self, *args):
        print(args)

    def _on_data_added(self, msg):
        self.data_items = self.data_items + [
            {
                'id': str(uuid.uuid4()),
                'name': msg.data.label,
                'locked': False,  # not bool(self.selected_viewer_item),
                'children': [
                    # {'id': 2, 'name': 'Calendar : app'},
                    # {'id': 3, 'name': 'Chrome : app'},
                    # {'id': 4, 'name': 'Webstorm : app'},
                ],
            }
        ]

    def _create_stack_item(self, container='gl-stack', children=None,
                           viewers=None):
        return {
            'id': str(uuid.uuid4()),
            'container': container,
            'children': children if children is not None else [],
            'viewers': viewers if viewers is not None else []}

    def _create_viewer_item(self, name, widget, tools, layer_options,
                            viewer_options):
        tools.borderless = True
        tools.tile = True

        return {
            'id': str(uuid.uuid4()),
            'widget': widget,
            'name': "Slider Test",
            'tools': tools,
            'layer_options': layer_options,
            'viewer_options': viewer_options,
            'selected_data_items': [],
            'collapse': True}

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        # Create the viewer item dictionary
        new_viewer_item = self._create_viewer_item(
            name="Slider Test",
            widget=view.figure_widget,
            tools=view.toolbar_selection_tools,
            layer_options=view.layer_options,
            viewer_options=view.viewer_options)

        new_stack_item = self._create_stack_item(
            container='gl-stack',
            children=[],
            viewers=[new_viewer_item])

        # Add viewer locally
        self.stack_items = self.stack_items + [
            new_stack_item
        ]

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        self._base_viewers[new_viewer_item['id']] = view

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

        settings = self.settings
        settings.update(config.get('settings'))
        self.settings = settings

        def compose_viewer_area(viewer_area_items):
            stack_items = []

            for item in viewer_area_items:
                stack_item = self._create_stack_item(
                    container=CONTAINER_TYPES[item.get('container')])

                stack_items.append(stack_item)

                for viewer in item.get('viewers', []):
                    view = viewer_registry.members.get(viewer['plot'])['cls'](
                        session=self.session)

                    viewer_item = self._create_viewer_item(
                        name=viewer.get('name'),
                        widget=view.figure_widget,
                        tools=view.toolbar_selection_tools,
                        layer_options=view.layer_options,
                        viewer_options=view.viewer_options)

                    stack_item.get('viewers').append(viewer_item)

                if len(item.get('children', [])) > 0:
                    child_stack_items = compose_viewer_area(item.get('children'))
                    stack_item['children'] = child_stack_items

            return stack_items

        if config.get('viewer_area') is not None:
            stack_items = compose_viewer_area(config.get('viewer_area'))
            self.stack_items = self.stack_items + stack_items

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(session=self.session)

            self.tool_items = self.tool_items + [{
                'name': name,
                'widget': tool
            }]

        for name in config.get('tray', []):
            tray = tray_registry.members.get(
                name).get('cls')(session=self.session)

            self.tray_items = self.tray_items + [{
                'name': name,
                'widget': tray
            }]
