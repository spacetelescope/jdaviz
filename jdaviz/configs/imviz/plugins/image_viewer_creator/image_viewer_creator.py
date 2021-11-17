from traitlets import List

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.registries import tool_registry
from jdaviz.configs.imviz.plugins.viewers import ImvizImageView

__all__ = ['ImageViewerCreator']


@tool_registry('g-image-viewer-creator')
class ImageViewerCreator(TemplateMixin):

    template_file = __file__, "image_viewer_creator.vue"
    viewer_types = List([]).tag(sync=True)

    def vue_create_image_viewer(self, *args, **kwargs):

        new_viewer_message = NewViewerMessage(
            ImvizImageView, data=None, sender=self)

        self.hub.broadcast(new_viewer_message)
