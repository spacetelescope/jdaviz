import os
import uuid

import ipyvuetify as v
import ipywidgets as w
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from ipykernel.comm import Comm
from traitlets import Any, Bool, Dict, Int, List, Unicode, observe

from jdaviz.core.events import (AddViewerMessage, RemoveItemMessage,
                                RemoveStackMessage, SplitStackMessage)
from jdaviz.core.template_mixin import TemplateMixin

from ...core.registries import viewers
from ...utils import load_template

__all__ = ['ViewerArea']


class Stack(TemplateMixin):
    template = load_template("stack.vue", __file__).tag(sync=True)
    items = List([]).tag(sync=True, **w.widget_serialization)
    tab = Any(0).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    drawer = Bool(False).tag(sync=True)
    overlay = Bool(False).tag(sync=True)
    data_items = List([]).tag(sync=True)
    selected_data_items = List([]).tag(sync=True)

    def __init__(self, item=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if item is not None:
            self.items = [item]

        # Setup data items
        self.data_items = [
            {
                'id': str(uuid.uuid4()),
                'name': x.label,
                'children': []
            }
            for x in self.data_collection
        ]

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._base_viewers = {}

    def _on_data_updated(self, msg=None):
        self.dc_items = [x.label for x in self.data_collection]

        self.data_items = self.data_items + [
            {
                'id': str(uuid.uuid4()),
                'name': msg.data.label,
                'children': [
                    # {'id': 2, 'name': 'Calendar : app'},
                    # {'id': 3, 'name': 'Chrome : app'},
                    # {'id': 4, 'name': 'Webstorm : app'},
                ],
            }
        ]

    @observe("selected_data_items")
    def _on_selected_data_items_changed(self, event):
        for uid in event['new']:
            [data_name] = [x['name'] for x in self.data_items if x['id'] == uid]
            # data = [x for x in self.data_collection if x.label == event][0]
            self._base_viewers.get(self.items[self.tab].get('id')).add_data(data_name)

    def add_item(self, item):
        # TODO: terrible hack to get around the fact that we can't store non-
        #  ipywidget items in the traitlet attributes. We still need a direct
        #  reference to the glupyter viewer object, which itself is not an
        #  ipywidget in order to access the `add_data` method.
        if 'base' in item:
            self._base_viewers[item['id']] = item['base']
            del item['base']

        self.items = self.items + [item]

    @observe('items')
    def items_changed(self, event):
        if len(event['new']) == 0:
            remove_stack_msg = RemoveStackMessage(self, sender=self)
            self.hub.broadcast(remove_stack_msg)

    def vue_data_selected(self, event):
        data = [x for x in self.data_collection if x.label == event][0]
        self._base_viewers.get(self.items[self.tab].get('id')).add_data(data)

    def vue_split_pane(self, direction):
        item = self.items[self.tab]
        split_stack_msg = SplitStackMessage(
            item, direction == 'horizontal', sender=self)
        self.hub.broadcast(split_stack_msg)

    def vue_close_tab(self, id):
        new_items = [x for x in self.items if x['id'] != id]
        self.items = new_items


class Item(TemplateMixin):
    template = load_template("item.vue", __file__).tag(sync=True)
    horizontal = Bool(False).tag(sync=True)
    stacks = List([]).tag(sync=True, **w.widget_serialization)

    def __init__(self, stack=None, horizontal=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.horizontal = horizontal

        if stack is not None:
            self.add_stack(stack)

        self.hub.subscribe(self, RemoveStackMessage,
                           handler=self._on_stack_removed)
        self.hub.subscribe(self, SplitStackMessage,
                           handler=self._on_stack_split)
        self.hub.subscribe(self, RemoveItemMessage,
                           handler=self._on_item_removed)

    def add_stack(self, stack):
        self.stacks = [stack]

    @observe('stacks')
    def stacks_changed(self, event):
        if len(event['new']) == 0:
            self.hub.broadcast(RemoveItemMessage(self, sender=self))

    def _on_stack_split(self, msg):
        if msg.sender not in self.stacks:
            return

        item = msg.item
        horizontal = msg.horizontal

        self.horizontal = horizontal

        stack1 = msg.sender
        item1 = Item(stack1, session=self.session)
        stack2 = Stack(item, session=self.session)
        item2 = Item(stack2, session=self.session)

        self.stacks = [item1, item2]

    def _on_stack_removed(self, msg):
        if msg.sender not in self.stacks:
            return

        self.stacks = [x for x in self.stacks if x is not msg.stack]

    def _on_item_removed(self, msg):
        if msg.sender not in self.stacks:
            return

        self.stacks = [x for x in self.stacks if x is not msg.item]


class ViewerArea(TemplateMixin):
    """
    The main viewer area component containing all instanced viewers.

    Attributes
    ----------
    viewers : list
        The collection of :class:~`Row` instances contained in this viewer
        area.
    drawer : bool
        The state of the drawer (shown or not shown).
    """
    template = load_template("viewer_area.vue", __file__).tag(sync=True)
    viewers = List([]).tag(sync=True, **w.widget_serialization)
    drawer = Bool(False).tag(sync=True)
    items = List([]).tag(sync=True, **w.widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Subscribe to the add viewer messages to trigger the creation of new
        #  tabs in the tab area.
        self.hub.subscribe(self, AddViewerMessage, handler=self._on_add_viewer)

    def _on_add_viewer(self, msg):
        """
        Callback for glue :class:~`AddViewerMessage` events. Parses the event
        and creates new `Row` or `Column` objects as necessary. Adds the new
        viewer instance to the viewer area.
        """
        msg.viewer.figure_widget.layout.width = '100%'
        msg.viewer.figure_widget.layout.height = 'calc(100% - 48px)'

        selection_tools = msg.viewer.toolbar_selection_tools
        selection_tools.borderless = True
        selection_tools.tile = True

        tab_item = {
            'id': str(uuid.uuid4()),
            'title': "TEST",
            'widget': msg.viewer.figure_widget,
            'tools': selection_tools,
            'layer_options': msg.viewer.layer_options,
            'viewer_options': msg.viewer.viewer_options,
            'drawer': False,
            'base': msg.viewer
        }

        if len(self.items) == 0:
            stack = Stack(session=self.session)
            item = Item(stack, session=self.session)
            self.items = [item]

        def find_stack(items):
            for item in items:
                if isinstance(item, Stack):
                    item.add_item(tab_item)
                    return True
                elif isinstance(item, Item):
                    if len(item.stacks) == 0:
                        # If we got here, most likely there's an Item object
                        #  with no Stack. Create one and add it.
                        stack = Stack(session=self.session)
                        items[0].add_stack(stack)

                return find_stack(item.stacks)

        find_stack(self.items)

    def parse_layout(self, layout):
        """
        Parses the layout dictionary from the :func:~`jdaviz.app.Application.load_configuration`
        method. Constructs any necessary `Row` or `Column` objects and
        instantiates any empty viewers defined as children.

        Parameters
        ----------
        layout : dict
            The dictionary containing the hierarchy of rows, columns, and
            viewer tabs to be created on application instantiation.
        """
        base_item = Item(horizontal=True, session=self.session)
        self.items = [base_item]

        for lrow in layout:
            row_item = Item(horizontal=False, session=self.session)
            base_item.stacks = base_item.stacks + [row_item]

            for lcol in lrow.get('row'):
                col_item = Item(horizontal=True, session=self.session)
                row_item.stacks = row_item.stacks + [col_item]

                for view in lcol.get('col'):
                    stack = Stack(session=self.session)

                    viewer = viewers.members.get(view)['cls'](self.session)
                    viewer.register_to_hub(self.hub)

                    viewer.figure_widget.layout.width = '100%'
                    viewer.figure_widget.layout.height = 'calc(100% - 48px)'

                    selection_tools = viewer.toolbar_selection_tools
                    selection_tools.borderless = True
                    selection_tools.tile = True

                    stack.add_item({
                        'id': str(uuid.uuid4()),
                        'title': "TEST",
                        'widget': viewer.figure_widget,
                        'tools': selection_tools,
                        'layer_options': viewer.layer_options,
                        'viewer_options': viewer.viewer_options,
                        'drawer': False,
                        'base': viewer
                    })

                    item = Item(session=self.session)
                    item.add_stack(stack)
                    col_item.stacks = col_item.stacks + [item]
