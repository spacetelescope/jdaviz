import os
from jdaviz.core.template_mixin import TemplateMixin
from traitlets import Unicode, List, Bool, Int, Any
import ipywidgets as w
from jdaviz.core.events import AddViewerMessage
from glue.core.message import DataCollectionAddMessage

import uuid
import ipyvuetify as v
from ...core.registries import viewers

__all__ = ['ViewerArea']


def load_template(file_name):
    with open(os.path.join(os.path.dirname(__file__), file_name)) as f:
        TEMPLATE = f.read()

    return Unicode(TEMPLATE)


slider1 = w.IntSlider(description='Slider 1', value=20)
slider2 = w.IntSlider(description='Slider 2', value=40)


class Column(TemplateMixin):
    template = load_template("column.vue").tag(sync=True)

    tab = Int(0).tag(sync=True)
    items = List([]).tag(sync=True, **w.widget_serialization)
    queue = List([])
    dc_items = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

        self._base_viewers = {}

        # self.items = self.items + [
        #     {
        #         'id': str(uuid.uuid4()),
        #         'title': "Viewers",
        #         'widget': None
        #     },
        #     {
        #         'id': str(uuid.uuid4()),
        #         'title': "Viewers",
        #         'widget': None
        #     }
        # ]

    def _on_data_added(self, msg):
        self.dc_items = self.dc_items + [msg.data.label]

    def vue_data_selected(self, event):
        print(event)
        data = [x for x in self.data_collection if x.label == event][0]
        print(data)
        self._base_viewers.get(self.items[self.tab].get('id')).add_data(data)

    def add_item(self, item):
        self._base_viewers[item['id']] = item['base']

        del item['base']

        self.items = self.items + [item]

    def remove_item(self, item):
        new_items = [x for x in self.items if x is not item]
        self.items = new_items

    def vue_close_tab(self, id):
        new_items = [x for x in self.items if x['id'] != id]
        self.items = new_items

    def vue_split_pane(self, direction):
        self.queue = self.queue + [{'style': direction,
                                    'content': self.items[self.tab]
                                    }]


class Row(TemplateMixin):
    template = load_template("row.vue").tag(sync=True)

    items = List([
    ]).tag(sync=True, **w.widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.add_column(Column(session=self.session))
        # self.add_column(Column(session=self.session))

    def add_column(self, col):
        self.items = self.items + [col]
        col.observe(self._split_column, names='queue')

    def remove_column(self, col):
        new_items = [x for x in self.items if x is not col]
        self.items = new_items

    def _split_column(self, event):
        direction = event['new'][0].get('direction')
        item = event['new'][0].get('content')

        new_col = Column(session=self.session)
        new_col.add_item(item)

        self.add_column(new_col)


class ViewerArea(TemplateMixin):
    template = load_template("viewer_area.vue").tag(sync=True)
    fab = Bool(False).tag(sync=True)
    viewers = List([]).tag(sync=True, **w.widget_serialization)

    drawer = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Subscribe to the add viewer messages to trigger the creation of new
        #  tabs in the tab area.
        self.hub.subscribe(self, AddViewerMessage, handler=self._add_viewer)

    def _add_viewer(self, msg):
        msg.viewer.figure_widget.layout.width = '100%'
        msg.viewer.figure_widget.layout.height = 'calc(100% - 48px)'

        selection_tools = msg.viewer.toolbar_selection_tools
        selection_tools.borderless = True
        selection_tools.tile = True

        if len(self.viewers) == 0:
            self.viewers = self.viewers + [Row(session=self.session)]

        if len(self.viewers[0].items) == 0:
            self.viewers[0].add_column(Column(session=self.session))

        self.viewers[0].items[0].add_item({
            'id': str(uuid.uuid4()),
            'title': "TEST",
            'widget': msg.viewer.figure_widget,
            'tools': selection_tools,
            'layer_options': msg.viewer.layer_options,
            'viewer_options': msg.viewer.viewer_options,
            'drawer': False,
            'base': msg.viewer
        })

        # TODO: fix this hack to get the traitlet to update
        # self.viewers = self.viewers + [[]]
        # self.viewers = self.viewers[:-1]

        # TODO: Fix this hack to get traitlets to update
        # self.viewers = self.viewers + [[]]
        # self.viewers = self.viewers[:-1]

    def parse_layout(self, layout):
        for lrow in layout:
            row = Row(session=self.session)
            self.viewers = self.viewers + [row]

            for lcol in lrow.get('row'):
                col = Column(session=self.session)
                row.add_column(col)

                for view in lcol.get('col'):
                    viewer = viewers.members.get(view)['cls'](session=self.session)

                    selection_tools = viewer.toolbar_selection_tools
                    selection_tools.borderless = True
                    selection_tools.tile = True

                    col.add_item({
                        'id': str(uuid.uuid4()),
                        'title': "TEST",
                        'widget': viewer.figure_widget,
                        'tools': selection_tools,
                        'layer_options': viewer.layer_options,
                        'viewer_options': viewer.viewer_options,
                        'drawer': False,
                        'base': viewer
                    })
