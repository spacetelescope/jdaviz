from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['ImageViewerCreator']


@viewer_creator_registry('Image', overwrite=True)
class ImageViewerCreator(BaseViewerCreator):
    template_file = __file__, "../base_viewer_creator.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_catalog_or_image_not_spectrum', 'is_not_wcs_only']
        self.viewer_label_default = 'Image'  # TODO: append suffix if taken

    @property
    def viewer_class(self):
        return ImvizImageView
