from traitlets import List

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import tool_registry, viewer_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['ViewerCreator']


@tool_registry('g-viewer-creator')
class ViewerCreator(TemplateMixin):
    template_file = __file__, "viewer_creator.vue"
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
