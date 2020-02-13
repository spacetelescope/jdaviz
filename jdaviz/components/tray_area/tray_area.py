import os

import ipywidgets as w
import numpy as np
from glue_jupyter.utils import validate_data_argument
from traitlets import Unicode, List, Bool, Any, Dict, Int

from ...core.events import (LoadDataMessage, DataSelectedMessage,
                            NewViewerMessage)
from ...core.registries import trays, viewers
from ...core.template_mixin import TemplateMixin
from ...components.data_tree import DataTree
from ..file_loader import FileLoader

__all__ = ['TrayArea']

with open(os.path.join(os.path.dirname(__file__), "tray_area.vue")) as f:
    TEMPLATE = f.read()


class TrayArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    drawer = Bool(True).tag(sync=True)
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

    base_items_tab = Int(0).tag(sync=True)
    base_items = List([
            {
                'id': 1,
                'title': "Data",
                'widget': "g-data-tree"
            }
        ]).tag(sync=True, **w.widget_serialization)

    plugin_items_tab = Int(0).tag(sync=True)
    plugin_items = List([]).tag(sync=True, **w.widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Attach tray plugins from the registries
        components = {'g-data-tree': DataTree(session=self.session),
                      'g-file-loader': FileLoader(session=self.session)}
        components.update({k: v.get('cls')(session=self.session)
                           for k, v in trays.members.items()})

        self.components = components

        # Load in the references to the viewer registry. Because traitlets
        #  can't serialize the actual viewer class reference, create a list of
        #  dicts containing just the viewer name and label.
        self.viewers = [{'name': k, 'label': v['label']}
                        for k, v in viewers.members.items()]

    def vue_create_viewer(self, name):
        viewer_cls = viewers.members[name]['cls']

        selected = self.components.get('g-data-tree').selected

        for idx in selected:
            data = validate_data_argument(self.data_collection,
                                          self.data_collection[idx])

            new_viewer_message = NewViewerMessage(
                viewer_cls, data=data, sender=self)

            self.hub.broadcast(new_viewer_message)
