from jdaviz.configs.rampviz.plugins.viewers import RampvizImageView
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['Ramp3DViewerCreator']


@viewer_creator_registry('3D Ramp', overwrite=True)
class Ramp3DViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_ramp_cube']
        self.viewer_label_default = '3D Ramp'

    @property
    def viewer_class(self):
        return RampvizImageView
