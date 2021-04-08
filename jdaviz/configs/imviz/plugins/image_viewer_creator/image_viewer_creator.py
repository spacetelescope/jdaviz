from traitlets import List

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.registries import tool_registry
from jdaviz.configs.imviz.plugins.viewers import ImVizImageView
from jdaviz.utils import load_template

__all__ = ['ImageViewerCreator']


@tool_registry('g-image-viewer-creator')
class ImageViewerCreator(TemplateMixin):

    template = load_template("image_viewer_creator.vue", __file__).tag(sync=True)
    viewer_types = List([]).tag(sync=True)

    def vue_create_image_viewer(self, *args, **kwargs):

        new_viewer_message = NewViewerMessage(
            ImVizImageView, data=None, sender=self)

        self.hub.broadcast(new_viewer_message)
