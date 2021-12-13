from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import LoadDataMessage
from traitlets import Unicode, Bool
import os
from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import tool_registry

__all__ = ['DataTools']


@tool_registry('g-data-tools')
class DataTools(TemplateMixin):
    template_file = __file__, "data_tools.vue"
    dialog = Bool(False).tag(sync=True)
    valid_path = Bool(True).tag(sync=True)
    error_message = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)

        self._file_upload = FileChooser(start_path)

        self.components = {'g-file-import': self._file_upload}

        self._file_upload.observe(self._on_file_path_changed, names='file_path')

    def _on_file_path_changed(self, event):
        if (self._file_upload.file_path is not None
                and not os.path.exists(self._file_upload.file_path)
                or not os.path.isfile(self._file_upload.file_path)):
            self.error_message = "No file exists at given path"
            self.valid_path = False
        else:
            self.error_message = ""
            self.valid_path = True

    def vue_load_data(self, *args, **kwargs):
        if self._file_upload.file_path is None:
            self.error_message = "No file selected"
        elif os.path.exists(self._file_upload.file_path):
            try:
                load_data_message = LoadDataMessage(self._file_upload.file_path, sender=self)
                self.hub.broadcast(load_data_message)
            except Exception:
                self.error_message = "An error occurred when loading the file"
            else:
                self.dialog = False
