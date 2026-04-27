import os
from traitlets import Any, Unicode, observe
from ipywidgets import widget_serialization
from solara import FileBrowser, reactive
import reacton
from pathlib import Path

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ['FileResolver', 'PresetFileResolver']


@loader_resolver_registry('file')
class FileResolver(BaseResolver):
    template_file = __file__, "file.vue"
    default_input = 'filepath'
    default_input_cast = str

    title = Unicode("Load Local File").tag(sync=True)
    file_chooser_widget = Any().tag(sync=True, **widget_serialization)
    filepath = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        # NOTE: file_chooser_dir must always be an absolute path or else its impossible to
        # navigate higher in the directory tree
        self.file_chooser_dir = reactive(Path(os.path.abspath(os.environ.get('JDAVIZ_START_DIR', os.path.curdir))))  # noqa
        self.filepath_reactive = reactive(self.filepath)
        self.file_chooser_widget_el = FileBrowser(directory=self.file_chooser_dir,
                                                  selected=self.filepath_reactive,
                                                  on_path_select=self._on_file_chooser_path_changed,
                                                  can_select=True)
        self.file_chooser_widget, rc = reacton.render(self.file_chooser_widget_el)
        super().__init__(*args, **kwargs)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['filepath'])

    @classmethod
    def from_input(cls, app, inp, **kwargs):
        # prevent errors from solara being raised if input is not valid
        if not isinstance(inp, (str, bytes, os.PathLike)):
            raise ValueError(f"'{inp}' is not a valid file path.")
        if not os.path.exists(inp) or not os.path.isfile(inp):
            raise ValueError(f"'{inp}' is not a valid file path.")
        return super().from_input(app, inp, **kwargs)

    def _on_file_chooser_path_changed(self, path):
        if self.filepath_reactive.value is not None:
            self.filepath = os.path.join(self.file_chooser_dir.value, self.filepath_reactive.value)
        else:
            self.filepath = ''

    @observe('filepath')
    def _on_filepath_changed(self, change):
        # when the filepath traitlet is changed, need to update the
        # file_chooser_widget to match the corresponding path
        if self.filepath == '':
            return
        self.filepath_reactive.value = Path(self.filepath)
        self._resolver_input_updated()
        if not os.path.exists(self.filepath) or not os.path.isfile(self.filepath):
            # consider empty if a directory or non-existent file is selected
            self.parsed_input_is_empty = True

    def _check_is_valid(self):
        if not os.path.exists(self.filepath):
            return False, 'Filepath does not exist.'

        if not os.path.isfile(self.filepath):
            return False, 'Filepath is not a file.'

        return True

    @property
    def default_label(self):
        return os.path.splitext(os.path.basename(self.filepath))[0] if self.filepath else None

    def parse_input(self):
        return self.filepath


class PresetFileResolver(FileResolver):
    """
    A FileResolver variant with a pre-set filepath that doesn't show
    the file browser widget. Used for programmatically adding files.

    This resolver behaves like the file resolver but hides the file browser
    inputs by setting hide_resolver_inputs=True, while still showing
    query results and importer selection.
    """

    def __init__(self, filepath, title=None, *args, **kwargs):
        # Validate filepath before initialization
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            raise ValueError(f"'{filepath}' is not a valid file path.")

        # Skip the FileBrowser widget initialization
        # Set these to None to avoid parent's __init__ trying to create them
        self.file_chooser_widget = None
        self.file_chooser_widget_el = None
        self.file_chooser_dir = None
        self.filepath_reactive = None

        # Call grandparent (BaseResolver) init directly to skip FileResolver's init
        BaseResolver.__init__(self, *args, **kwargs)

        self.filepath = filepath

        # Set custom title if provided
        if title is not None:
            self.title = title

        # Override to hide file browser inputs
        self.hide_resolver_inputs = True

    def _on_file_chooser_path_changed(self, path):
        # Override to prevent errors when file_chooser doesn't exist
        pass

    @observe('filepath')
    def _on_filepath_changed(self, change):
        # Simplified version that doesn't update UI widgets
        if self.filepath == '':
            return
        self._resolver_input_updated()
        if not os.path.exists(self.filepath) or not os.path.isfile(self.filepath):
            self.parsed_input_is_empty = True
