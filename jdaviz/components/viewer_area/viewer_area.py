import os
from jdaviz.core.template_mixin import TemplateMixin
from traitlets import Unicode, List, Bool
import ipywidgets as w
from jdaviz.core.events import AddViewerMessage
import uuid

__all__ = ['ViewerArea']

with open(os.path.join(os.path.dirname(__file__), "viewer_area.vue")) as f:
    TEMPLATE = f.read()


class ViewerArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    fab = Bool(False).tag(sync=True)

    viewers = List([
        [
            {
                'tab': 0,
                'items': [
                    {
                        'id': '1',
                        'title': "Option",
                        'widget': None
                    },
                    {
                        'id': '2',
                        'title': "Viewers",
                        'widget': None
                    }
                ]
            },
            {
                'tab': 0,
                'items': [
                    {
                        'id': '3',
                        'title': "Component",
                        'widget': None
                    },
                    {
                        'id': '4',
                        'title': "Layout",
                        'widget': None
                    }
                ]
            }
        ],
        [
            {
                'tab': 0,
                'items': [
                    {
                        'id': '11',
                        'title': "Armature",
                        'widget': None
                    },
                    {
                        'id': '12',
                        'title': "User",
                        'widget': None
                    }
                ]
            }
        ]
    ]).tag(sync=True, **w.widget_serialization)

    items = List([
          { 'title': 'Home', 'icon': 'dashboard' },
          { 'title': 'About', 'icon': 'question_answer' }
    ]).tag(sync=True)

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
            self.viewers.append([])

        if len(self.viewers[0]) == 0:
            self.viewers[0].append({'tab': 0, 'items': []})

        self.viewers[0][0]['items'].append({
            'id': str(uuid.uuid4()),
            'title': "TEST",
            'widget': msg.viewer.figure_widget,
            'tools': selection_tools,
            'layer_options': msg.viewer.layer_options,
            'viewer_options': msg.viewer.viewer_options,
            'drawer': False
        })

        # TODO: fix this hack to get the traitlet to update
        self.viewers = self.viewers + [[]]
        self.viewers = self.viewers[:-1]

    def vue_close_tab(self, id):
        for row in self.viewers:
            for col in row:
                for item in col['items']:
                    if item['id'] == id:
                        col['items'].remove(item)

                        if len(col['items']) == 0:
                            row.remove(col)

                        break

            if len(row) == 0:
                self.viewers.remove(row)

        # TODO: Fix this hack to get traitlets to update
        self.viewers = self.viewers + [[]]
        self.viewers = self.viewers[:-1]

    def vue_split_pane(self, *args):
        print(args)