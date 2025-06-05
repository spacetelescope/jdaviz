from jdaviz.configs.default.plugins.viewers import ScatterViewer
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['ScatterViewerCreator']


@viewer_creator_registry('Scatter', overwrite=True)
class ScatterViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.viewer_label_default = 'Scatter'  # TODO: append suffix if taken

    @property
    def viewer_class(self):
        return ScatterViewer
