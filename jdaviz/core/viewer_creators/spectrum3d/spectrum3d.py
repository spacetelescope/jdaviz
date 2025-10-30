from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['Spectrum3DViewerCreator']


@viewer_creator_registry('3D Spectrum', overwrite=True)
class Spectrum3DViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_flux_cube']
        self.viewer_label_default = '3D Spectrum'

    @property
    def viewer_class(self):
        return CubevizImageView
