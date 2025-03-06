import os
from traitlets import Unicode, observe

from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ['FileResolver']


@loader_resolver_registry('file')
class FileResolver(BaseResolver):
    template_file = __file__, "file.vue"
    default_input = 'filepath'

    filepath = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_upload = FileChooser(start_path)
        self._file_upload.observe(self._on_file_upload_path_changed, names='file_path')
        self.components = {'g-file-import': self._file_upload}
        super().__init__(*args, **kwargs)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['filepath'])

    def _on_file_upload_path_changed(self, event):
        self.filepath = self._file_upload.file_path

    @observe('filepath')
    def _on_filepath_changed(self, change):
        if self._file_upload.file_path != change['new']:
            path, file = os.path.split(change['new'])
            self._file_upload._set_form_values(path, file)
        self._update_format_items()

    @property
    def is_valid(self):
        if self._file_upload.file_path is None:
            return False
        return os.path.exists(self._file_upload.file_path) and os.path.isfile(self._file_upload.file_path)  # noqa

    def __call__(self):
        return self._file_upload.file_path
