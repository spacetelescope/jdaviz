import os

from traitlets import Unicode, Bool

from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin

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
        if self._file_upload.file_path is None:
            self.valid_path = False
        elif (not os.path.exists(self._file_upload.file_path)
              or not os.path.isfile(self._file_upload.file_path)):
            self.valid_path = False
        else:
            self.valid_path = True

    def vue_load_data(self, *args, **kwargs):
        if self._file_upload.file_path is None:
            self.error_message = "No file selected"
        elif os.path.exists(self._file_upload.file_path):
            try:
                # NOTE: Helper loader does more stuff than native Application loader.
                self.app._jdaviz_helper.load_data(self._file_upload.file_path)
            except Exception as err:
                self.error_message = f"An error occurred when loading the file: {repr(err)}"
            else:
                self.dialog = False
