from jdaviz.configs.rampviz.plugins.viewers import RampvizImageView
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['RampDiff3DViewerCreator']


@viewer_creator_registry('3D Ramp Diff', overwrite=True)
class RampDiff3DViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_flux_cube']  # TODO: better filter
        self.viewer_label_default = '3D Ramp Diff'

    @property
    def viewer_class(self):
        return RampvizImageView
