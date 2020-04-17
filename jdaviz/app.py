import os
import uuid

import ipywidgets as w
import pkg_resources
import yaml
from glue.core import BaseData
from glue.core.autolinking import find_possible_links
from glue.core.message import DataCollectionAddMessage
from glue.core.state_objects import State
from echo import (CallbackProperty, ListCallbackProperty,
                  DictCallbackProperty)
from glue_jupyter.app import JupyterApplication
from glue_jupyter.state_traitlets_helpers import GlueState
from ipygoldenlayout import GoldenLayout
from ipysplitpanes import SplitPanes
from traitlets import Dict, observe, List

from .core.events import LoadDataMessage, NewViewerMessage
from .core.registries import tool_registry, tray_registry, viewer_registry
from .core.template_mixin import TemplateMixin
from .utils import load_template

__all__ = ['Application']

SplitPanes()
GoldenLayout()

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')


class ApplicationState(State):
    drawer = CallbackProperty(
        False, docstring="State of the plugins drawer.")

    settings = DictCallbackProperty({
        'visible': {
            'menu_bar': True,
            'toolbar': True,
            'tray': True,
            'tab_headers': True,
        },
        'context': {
            'notebook': {
                'max_height': '600px'
            }
        },
        'layout': {
        }
    }, docstring="Top-level application settings.")

    data_items = ListCallbackProperty(
        docstring="List of data items parsed from the Glue data collection.")

    tool_items = ListCallbackProperty(
        docstring="Collection of toolbar items displayed in the application.")

    tray_items = ListCallbackProperty(
        docstring="List of plugins displayed in the sidebar tray area.")

    stack_items = ListCallbackProperty(
        docstring="Nested collection of viewers constructed to support the "
                  "Golden Layout viewer area.")


class Application(TemplateMixin):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    state = GlueState().tag(sync=True)

    template = load_template("app.vue", __file__).tag(sync=True)

    components = Dict({'g-viewer-tab': load_template(
        "container.vue", __file__, traitlet=False)}).tag(
            sync=True, **w.widget_serialization)

    def __init__(self, configuration=None, *args, **kwargs):
        self.state = ApplicationState()

        super().__init__(*args, **kwargs)

        self._application_handler = JupyterApplication()

        plugins = {
            entry_point.name: entry_point.load()
            for entry_point
            in pkg_resources.iter_entry_points(group='plugins')}

        # Create a dictionary for holding non-ipywidget viewer objects
        self._viewer_store = {}

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

    @property
    def data_collection(self):
        return self._application_handler.data_collection

    def load_data(self, path):
        self._application_handler.load_data(path)

        # Attempt to link the data
        links = find_possible_links(self.data_collection)

        # self.data_collection.add_link(links['Astronomy WCS'])

    def get_viewer(self, reference):
        return self._viewer_by_reference(reference)

    def get_data(self, reference, cls=None):
        viewer = self.get_viewer(reference)
        cls = cls or viewer.default_class

        data = [layer_state.layer.get_object(cls=cls)
                for layer_state in viewer.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

        return data

    def add_data(self, reference, data, name=None):
        name = name or "New Data"
        self.data_collection[name] = data

        viewer_item = self._viewer_item_by_reference(reference)

        # Enable selection of data in viewer data list
        viewer_item['selected_data_items'].append(name)

    def _viewer_by_id(self, vid):
        return self._viewer_store.get(vid)

    def _viewer_item_by_id(self, vid):
        def find_viewer_item(stack_items):
            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['id'] == vid:
                        return viewer_item

                if len(stack_item.get('children')) > 0:
                    return find_viewer_item(stack_item.get('children'))

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    def _viewer_by_reference(self, ref):
        viewer_item = self._viewer_item_by_reference(ref)

        return self._viewer_store[viewer_item['id']]

    def _viewer_item_by_reference(self, ref):
        def find_viewer_item(stack_items):
            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['reference'] == ref:
                        return viewer_item

                if len(stack_item.get('children')) > 0:
                    return find_viewer_item(stack_item.get('children'))

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    @observe('state.stack_items')
    def vue_relayout(self, *args, **kwargs):
        def resize(stack_items):
            for stack in stack_items:
                for viewer_item in stack.get('viewers'):
                    viewer_id = viewer_item['id']
                    viewer = self._viewer_store.get(viewer_id)

                    viewer.layout.height = '99.9%'
                    viewer.layout.height = '100%'

                if len(stack.get('children')) > 0:
                    resize(stack.get('children'))

        resize(self.state.stack_items)

    def vue_remove_component(self, cid):
        def remove(stack_items):
            for stack in stack_items:
                if stack['id'] == cid:
                    stack_items.remove(stack)

                for viewer in stack['viewers']:
                    if viewer['id'] == cid:
                        stack['viewers'].remove(viewer)

                if len(stack.get('children', [])) > 0:
                    stack['children'] = remove(stack['children'])

            return stack_items

        # new_stack_items =
        remove([x for x in self.state.stack_items])
        # self.state.stack_items = new_stack_items

    def vue_data_item_selected(self, event):
        viewer_id, selected_items = event['id'], event['selected_items']

        # Find the active viewer
        viewer_item = self._viewer_item_by_id(viewer_id)
        viewer = self._viewer_by_id(viewer_id)

        # Update the store selected data items
        viewer_item['selected_data_items'] = selected_items
        data_ids = viewer_item['selected_data_items']

        active_data_labels = []

        # Include any selected data in the viewer
        for data_id in data_ids:
            [label] = [x['name'] for x in self.state.data_items
                       if x['id'] == data_id]

            active_data_labels.append(label)

            [data] = [x for x in self.data_collection if x.label == label]

            viewer.add_data(data)

            add_data_message = AddDataMessage(data, active_viewer, sender=self)
            self.hub.broadcast(add_data_message)

        # Remove any deselected data objects from viewer
        viewer_data = [layer_state.layer
                       for layer_state in viewer.state.layers
                       if hasattr(layer_state, 'layer') and
                       isinstance(layer_state.layer, BaseData)]

        for data in viewer_data:
            if data.label not in active_data_labels:
                viewer.remove_data(data)

    def vue_remove_viewer(self, *args):
        viewer_id, stack_id = args[0]
        viewer_item = self._viewer_by_id(viewer_id, stack_id)

        # temp_stack_items = self.state.stack_items

        for stack in self.state.stack_items:
            if stack['id'] == stack_id:
                stack['viewers'].remove(viewer_item)
                break

        # self.state.stack_items = []
        # self.state.stack_items = temp_stack_items

    def _on_data_added(self, msg):
        self.state.data_items.append({
            'id': str(uuid.uuid4()),
            'name': msg.data.label,
            'locked': False,
            'children': []})

    @staticmethod
    def _create_stack_item(container='gl-stack', children=None, viewers=None):
        children = [] if children is None else children
        viewers = [] if viewers is None else viewers

        return {
            'id': str(uuid.uuid4()),
            'container': container,
            'children': children,
            'viewers': viewers}

    @staticmethod
    def _create_viewer_item(viewer, name=None, reference=None):
        tools = viewer.toolbar_selection_tools
        tools.borderless = True
        tools.tile = True

        return {
            'id': str(uuid.uuid4()),
            'name': name or "Unnamed Viewer",
            'widget': "IPY_MODEL_" + viewer.figure_widget.model_id,
            'tools': "IPY_MODEL_" + viewer.toolbar_selection_tools.model_id,
            'layer_options': "IPY_MODEL_" + viewer.layer_options.model_id,
            'viewer_options': "IPY_MODEL_" + viewer.viewer_options.model_id,
            'selected_data_items': [],
            'collapse': False,
            'reference': reference}

    def _on_new_viewer(self, msg):
        viewer = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            viewer.state.x_att = x

        # Create the viewer item dictionary
        new_viewer_item = self._create_viewer_item(
            viewer=viewer)

        new_stack_item = self._create_stack_item(
            container='gl-stack',
            viewers=[new_viewer_item])

        # Add viewer locally
        self.state.stack_items.append(new_stack_item)

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        self._viewer_store[new_viewer_item['id']] = viewer

        return viewer

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

        settings = {k: v for k, v in self.state.settings.items()}
        settings.update(config.get('settings'))
        self.state.settings = settings

        def compose_viewer_area(viewer_area_items):
            stack_items = []

            for item in viewer_area_items:
                stack_item = self._create_stack_item(
                    container=CONTAINER_TYPES[item.get('container')])

                stack_items.append(stack_item)

                for view in item.get('viewers', []):
                    viewer = self._application_handler.new_data_viewer(
                        viewer_registry.members.get(view['plot'])['cls'],
                        data=None, show=False)

                    viewer_item = self._create_viewer_item(
                        name=view.get('name'),
                        viewer=viewer,
                        reference=view.get('reference'))

                    self._viewer_store[viewer_item['id']] = viewer

                    stack_item.get('viewers').append(viewer_item)

                if len(item.get('children', [])) > 0:
                    child_stack_items = compose_viewer_area(
                        item.get('children'))
                    stack_item['children'] = child_stack_items

            return stack_items

        if config.get('viewer_area') is not None:
            stack_items = compose_viewer_area(config.get('viewer_area'))
            self.state.stack_items.extend(stack_items)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(session=self.session)

            self.state.tool_items.append({
                'name': name,
                'widget': "IPY_MODEL_" + tool.model_id
            })

        for name in config.get('tray', []):
            tray = tray_registry.members.get(
                name).get('cls')(session=self.session)

            self.state.tray_items.append({
                'name': name,
                'widget': "IPY_MODEL_" + tray.model_id
            })
