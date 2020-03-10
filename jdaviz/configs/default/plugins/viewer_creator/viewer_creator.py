import os

from glue_jupyter.utils import validate_data_argument
from traitlets import List, Unicode, observe

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import tool_registry, viewer_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['ViewerCreator']


@tool_registry('g-viewer-creator')
class ViewerCreator(TemplateMixin):
    template = load_template("viewer_creator.vue", __file__).tag(sync=True)
    viewer_types = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load in the references to the viewer registry. Because traitlets
        #  can't serialize the actual viewer class reference, create a list of
        #  dicts containing just the viewer name and label.
        self.viewer_types = [{'name': k, 'label': v['label']}
                             for k, v in viewer_registry.members.items()]

    def vue_create_viewer(self, name):
        viewer_cls = viewer_registry.members[name]['cls']

        # selected = self.components.get('g-data-tree').selected

        # for idx in selected:
        #     data = validate_data_argument(self.data_collection,
        #                                   self.data_collection[idx])

        new_viewer_message = NewViewerMessage(
            viewer_cls, data=None, sender=self)

        self.hub.broadcast(new_viewer_message)
