import os
import tempfile
import uuid

import ipywidgets as w
from traitlets import Dict

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['FileImport']


@tool_registry('g-file-import')
class FileImport(TemplateMixin):
    chosen_file = Dict().tag(sync=True)
    template = load_template("file_import.vue", __file__).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._file_upload = w.FileUpload(accept='*')
        self.components = {'g-file-import': self._file_upload}

        self._file_upload.observe(self.on_counter_changed, names=['_counter'])

    def on_counter_changed(self, event):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_name = str(uuid.uuid4())
            file_path = os.path.join(tmp_dir, file_name)

            with open(file_path, "wb") as tmp_file:
                tmp_file.write(list(self._file_upload.value.values())[-1]['content'])

            self.app.load_data(file_path)\


