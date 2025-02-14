import os
from traitlets import Unicode

from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import PluginTemplateMixin


@loader_resolver_registry('filepath')
class FilepathResolver(PluginTemplateMixin):
    template_file = __file__, "filepath.vue"

    error_message = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_upload = FileChooser(start_path)
        self.components = {'g-file-import': self._file_upload}
        super().__init__(*args, **kwargs)

    @property
    def is_valid(self):
        return os.path.exists(self._file_upload.file_path)

    def __call__(self):
        return self._file_upload.file_path