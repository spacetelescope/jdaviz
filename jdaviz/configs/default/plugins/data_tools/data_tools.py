from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from jdaviz.core.events import LoadDataMessage
from traitlets import Unicode, Bool, observe
import os
from ipyfilechooser import FileChooser
from jdaviz.core.registries import tool_registry

__all__ = ['DataTools']


@tool_registry('g-data-tools')
class DataTools(TemplateMixin):
    template = load_template("data_tools.vue", __file__).tag(sync=True)
    file_path = Unicode("").tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    valid_path = Bool(True).tag(sync=True)
    error_message = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._file_upload = FileChooser(os.path.expanduser('~'), use_dir_icons=True)

        self.components = {'g-file-import': self._file_upload}

        self._file_upload.register_callback(self._on_file_path_changed)

    @observe("file_path")
    def _on_file_path_changed(self, event):
        if not os.path.exists(event['new']) or not os.path.isfile(event['new']):
            self.error_message = "No file exists at given path"
            self.valid_path = False
        else:
            self.error_message = ""
            self.valid_path = True

    def vue_load_data(self, *args, **kwargs):
        if os.path.exists(self.file_path):
            load_data_message = LoadDataMessage(self.file_path, sender=self)
            self.hub.broadcast(load_data_message)
            self.dialog = False
