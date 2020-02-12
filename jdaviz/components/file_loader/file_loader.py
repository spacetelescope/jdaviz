from ...core.template_mixin import TemplateMixin
from ...utils import load_template
from traitlets import Unicode, Bool, observe
import os
from ...core.events import LoadDataMessage

__all__ = ['FileLoader']


class FileLoader(TemplateMixin):
    template = load_template("file_loader.vue", __file__).tag(sync=True)
    file_path = Unicode("").tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    valid_path = Bool(True).tag(sync=True)
    error_message = Unicode().tag(sync=True)

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