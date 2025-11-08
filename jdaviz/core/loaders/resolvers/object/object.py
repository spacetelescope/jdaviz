import os
from pathlib import Path
from traitlets import Unicode

from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.core.template_mixin import CustomToolbarToggleMixin
from jdaviz.core.tools import ICON_DIR


@loader_resolver_registry('object')
class ObjectResolver(BaseResolver, CustomToolbarToggleMixin):
    template_file = __file__, "object.vue"
    default_input = 'object'
    requires_api_support = True

    object_repr = Unicode("").tag(sync=True)
    footprint_select_icon = Unicode(read_icon(os.path.join(
        ICON_DIR, 'footprint_select.svg'), 'svg+xml')).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._object = None
        super().__init__(*args, **kwargs)

        def custom_toolbar(viewer):
            if hasattr(self, 'observation_table') and self.observation_table is not None:
                if 's_region' in self.observation_table.headers_avail:
                    return viewer.toolbar._original_tools_nested[:3] + [['jdaviz:selectregion']], 'jdaviz:selectregion'
            return None, None

        self.custom_toolbar.callable = custom_toolbar
        self.custom_toolbar.name = "Footprint Selection"

    def toggle_custom_toolbar(self):
        """Override to control footprint display when toolbar is toggled."""
        super().toggle_custom_toolbar()

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['object'])

    @property
    def is_valid(self):
        if isinstance(self.object, str):
            # reject strings that should go through file
            # or url resolvers instead
            if Path(self.object).exists():
                return False
            if self.object.strip().startswith(('http://', 'https://',
                                               'ftp://', 's3://', 'mast://')):
                return False
        return not isinstance(self.object, Path)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, obj):
        self._object = obj
        self.object_repr = f"<{obj.__class__.__name__} object>"
        self._resolver_input_updated()

    def parse_input(self):
        return self.object
