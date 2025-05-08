from jdaviz.configs.specviz.plugins.viewers import Spectrum2DViewer
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['Spectrum2DViewerCreator']


@viewer_creator_registry('2D Spectrum', overwrite=True)
class Spectrum2DViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_2d_spectrum_or_trace']
        self.viewer_label_default = '2D Spectrum'

    @property
    def viewer_class(self):
        return Spectrum2DViewer
