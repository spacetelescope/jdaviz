from jdaviz.configs.rampviz.plugins.viewers import RampvizProfileView
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['RampIntegrationViewerCreator']


@viewer_creator_registry('Ramp Integration', overwrite=True)
class RampIntegrationViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_ramp_integration']
        self.viewer_label_default = 'Ramp Integration'

    @property
    def viewer_class(self):
        return RampvizProfileView
