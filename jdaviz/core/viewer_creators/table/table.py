from jdaviz.configs.default.plugins.viewers import JdavizTableViewer
from jdaviz.core.user_api import ViewerCreatorUserApi
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['TableViewerCreator']


@viewer_creator_registry('Table', overwrite=True)
class TableViewerCreator(BaseViewerCreator):
    template_file = __file__, "table.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_catalog']
        self.viewer_label_default = 'Table'

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self)

    @property
    def viewer_class(self):
        return JdavizTableViewer
