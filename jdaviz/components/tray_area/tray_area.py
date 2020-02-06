import os

import ipywidgets as w
import numpy as np
from glue_jupyter.utils import validate_data_argument
from traitlets import Unicode, List, Bool, Any, Dict

from ...core.events import (LoadDataMessage, DataSelectedMessage,
                            NewViewerMessage)
from ...core.registries import trays, viewers
from ...core.template_mixin import TemplateMixin
from ...components.data_tree import DataTree

__all__ = ['TrayArea']

with open(os.path.join(os.path.dirname(__file__), "tray_area.vue")) as f:
    TEMPLATE = f.read()


class TrayArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    drawer = Bool(True).tag(sync=True)
    valid = Bool(True).tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    data = Unicode("""
    {
        files: undefined
    }
    """).tag(sync=True)
    methods = Unicode("""
    {
        returnFiles() {
            return this.files && this.files.name;
        }
    }
    """).tag(sync=True)

    viewers = List([]).tag(sync=True)

    tray_items = List([
        [
            {
                'tab': 0,
                'items': [
                    {
                        'id': 1,
                        'title': "Data",
                        'widget': "g-data-tree"
                    },
                ]
            }
        ],
        [
            {
                'tab': 0,
                'items': [
                    {
                        'id': 11,
                        'title': "Test Plugin",
                        'widget': None
                    },
                    {
                        'id': 12,
                        'title': "Test Plugin",
                        'widget': None
                    },
                    {
                        'id': 13,
                        'title': "Test Plugin",
                        'widget': None
                    }
                ]
            }
        ]
    ]).tag(sync=True, **w.widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Attach tray plugins from the registries
        components = {'g-data-tree': DataTree(session=self.session)}
        components.update({k: v.get('cls')(session=self.session)
                           for k, v in trays.members.items()})

        self.components = components

        # Load in the references to the viewer registry. Because traitlets
        #  can't serialize the actual viewer class reference, create a list of
        #  dicts containing just the viewer name and label.
        self.viewers = [{'name': k, 'label': v['label']}
                        for k, v in viewers.members.items()]

    def vue_load_data(self, *args, **kwargs):
        self.dialog = False
        return
        # TODO: hack because of current incompatibility with ipywidget types
        #  and vuetify templates.
        for path in ["/Users/nearl/data/single_g235h-f170lp_x1d.fits"]:
            load_data_message = LoadDataMessage(path, sender=self)
            self.hub.broadcast(load_data_message)

        self.dialog = False

    def vue_file_inputted(self, *args, **kwargs):
        print(args, kwargs)

    def vue_create_viewer(self, name):
        viewer_cls = viewers.members[name]['cls']

        selected = self.components.get('g-data-tree').selected

        for idx in selected:
            data = validate_data_argument(self.data_collection,
                                          self.data_collection[idx])

            new_viewer_message = NewViewerMessage(
                viewer_cls, data=data, sender=self)

            self.hub.broadcast(new_viewer_message)
