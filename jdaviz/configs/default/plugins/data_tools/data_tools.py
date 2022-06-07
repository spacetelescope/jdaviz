from pathlib import Path
from typing import Callable, Optional
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import LoadDataMessage
from traitlets import Unicode, Bool
import os
from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.registries import tool_registry
import solara as sol
import react_ipywidgets as react
__all__ = ['DataTools']


@tool_registry('g-data-tools')
class DataTools(TemplateMixin):
    template_file = __file__, "data_tools.vue"
    dialog = Bool(False).tag(sync=True)
    error_message = Unicode().tag(sync=True)
    directory = Unicode(None, allow_none=True).tag(sync=True)
    file = Unicode(None, allow_none=True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        start_path = str(Path(start_path).resolve())

        def on_directory_change(directory : Path):
            self.directory = str(directory)

        def on_file_open(file : Path):
            self._load(file)

        def on_path_select(path : Optional[Path]):
            if path is None:
                self.directory = None
                self.file = None
            else:
                if path.is_dir():
                    self.directory = str(path)
                else:
                    self.file = str(path)

        element = sol.FileBrowser(start_path,
                                  on_directory_change=on_directory_change,
                                  on_file_open=on_file_open,
                                  on_path_select=on_path_select,
                                  can_select=True,
                                  )
        self._file_upload, rc = react.render(element)

        self.components = {'g-file-import': self._file_upload}

    def _load(self, path : Path):
        try:
            load_data_message = LoadDataMessage(str(path), sender=self)
            self.hub.broadcast(load_data_message)
        except Exception:
            self.error_message = "An error occurred when loading the file"
        else:
            self.dialog = False

    def vue_load_file(self, *args, **kwargs):
        self._load(Path(self.file))

    def vue_load_directory(self, *args, **kwargs):
        self._load(Path(self.directory))
