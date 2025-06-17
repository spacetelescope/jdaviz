from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['Spectrum1DViewerCreator']


@viewer_creator_registry('1D Spectrum', overwrite=True)
class Spectrum1DViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_spectrum']
        self.viewer_label_default = '1D Spectrum'  # TODO: append suffix if taken

    @property
    def viewer_class(self):
        return Spectrum1DViewer
