import os
from traitlets import Unicode

from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver


@loader_resolver_registry('filepath')
class FilepathResolver(BaseResolver):
    template_file = __file__, "filepath.vue"

    error_message = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_upload = FileChooser(start_path)
        self._file_upload.observe(self._on_file_path_changed, names='file_path')
        self.components = {'g-file-import': self._file_upload}
        super().__init__(*args, **kwargs)

    def _on_file_path_changed(self, event):
        self.format._update_items()

    @property
    def is_valid(self):
        if self._file_upload.file_path is None:
            return False
        return os.path.exists(self._file_upload.file_path) and os.path.isfile(self._file_upload.file_path)  # noqa

    def __call__(self):
        return self._file_upload.file_path
