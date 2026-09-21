from jdaviz.configs.default.plugins.viewers import (JdavizTableViewer,
                                                    JdavizSourceCatalogTableViewer,
                                                    JdavizSpectralLineListTableViewer)
from jdaviz.core.user_api import ViewerCreatorUserApi
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry


__all__ = ['TableViewerCreator', 'SourceCatalogTableViewerCreator',
           'SpectralLineListTableViewerCreator']


@viewer_creator_registry('Table', overwrite=True)
class TableViewerCreator(BaseViewerCreator):
    template_file = __file__, "table.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_generic_table']
        self.viewer_label_default = 'Table'

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self)

    @property
    def viewer_class(self):
        return JdavizTableViewer


@viewer_creator_registry('Source Catalog Table', overwrite=True)
class SourceCatalogTableViewerCreator(BaseViewerCreator):
    template_file = __file__, "table.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_source_catalog_table']
        self.viewer_label_default = 'JdavizSourceCatalogTableViewer'

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self)

    @property
    def viewer_class(self):
        return JdavizSourceCatalogTableViewer


@viewer_creator_registry('Spectral Line List Table', overwrite=True)
class SpectralLineListTableViewerCreator(BaseViewerCreator):
    template_file = __file__, "table.vue"

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.dataset.filters = ['is_spectral_lines_list_table']
        self.viewer_label_default = 'JdavizSpectralLineListTableViewer'

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self)

    @property
    def viewer_class(self):
        return JdavizSpectralLineListTableViewer
