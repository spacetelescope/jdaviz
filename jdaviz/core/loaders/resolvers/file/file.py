import os
from traitlets import Any, Unicode, observe
from ipywidgets import widget_serialization
from solara import FileBrowserMultiple, reactive
import reacton
from pathlib import Path

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ['FileResolver', 'PresetFileResolver']


def _as_path_list(filepath):
    if isinstance(filepath, list):
        return filepath
    return [filepath] if filepath else []


@loader_resolver_registry('file')
class FileResolver(BaseResolver):
    template_file = __file__, "file.vue"
    default_input = 'filepath'
    default_input_cast = str

    title = Unicode("Load Local File").tag(sync=True)
    file_chooser_widget = Any().tag(sync=True, **widget_serialization)
    # a single path (str) or list of paths
    filepath = Any('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._updating_filepath = False
        # NOTE: file_chooser_dir must always be an absolute path or else its impossible to
        # navigate higher in the directory tree
        self.file_chooser_dir = reactive(Path(os.path.abspath(os.environ.get('JDAVIZ_START_DIR', os.path.curdir))))  # noqa
        self.filepath_reactive = reactive(self.filepath)
        self.file_chooser_widget_el = FileBrowserMultiple(directory=self.file_chooser_dir,
                                                          selected=self.filepath_reactive,
                                                          on_paths_select=self._on_file_chooser_path_changed)  # noqa
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
        if not os.path.exists(inp):
            raise ValueError(f"'{inp}' is not a valid file path.")
        return super().from_input(app, inp, **kwargs)

    def _on_file_chooser_path_changed(self, paths):
        filepaths = [str(path) for path in paths]
        self._updating_filepath = True
        try:
            self.filepath = filepaths[0] if len(filepaths) <= 1 else filepaths
        finally:
            self._updating_filepath = False

    @observe('filepath')
    def _on_filepath_changed(self, change):
        if not self._updating_filepath:
            # filepath was set directly (e.g. via the API) rather than through the file
            # browser widget: sync the widget's multi-select state to match
            if self.filepath_reactive is not None:
                self.filepath_reactive.value = [Path(p) for p in _as_path_list(self.filepath)]
        if not self.filepath:
            return
        self._resolver_input_updated()
        if not all(os.path.exists(p) for p in _as_path_list(self.filepath)):
            # consider empty if a non-existent path is selected
            self.parsed_input_is_empty = True

    def _check_is_valid(self):
        """
        Checks if the input is a valid file path.

        The output of this method is wrapped by the IsValidWrapper
        helper class that converts the string to an inverted boolean,
        i.e. empty string => True, non-empty string => False
        since the string (when filled) carries error information.
        Furthermore, the actual 'is_valid' check is handled by the ValidatorMixin
        that wraps the check in a try/except statement so that individual
        '_check_is_valid' calls no longer need to catch potential failures.
        """
        for path in _as_path_list(self.filepath):
            if not os.path.exists(path):
                return 'Filepath does not exist.'

        return ''

    @property
    def default_label(self):
        paths = _as_path_list(self.filepath)
        return os.path.splitext(os.path.basename(paths[0]))[0] if paths else None

    def _default_label_for_output(self, output_index):
        try:
            return os.path.splitext(os.path.basename(_as_path_list(self.filepath)[output_index]))[0]  # noqa
        except IndexError:
            return super()._default_label_for_output(output_index)

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
        if not os.path.exists(filepath):
            raise ValueError(f"'{filepath}' is not a valid file path.")

        # Skip the FileBrowser widget initialization
        # Set these to None to avoid parent's __init__ trying to create them
        self.file_chooser_widget = None
        self.file_chooser_widget_el = None
        self.file_chooser_dir = None
        self.filepath_reactive = None
        self._updating_filepath = False

        # Call grandparent (BaseResolver) init directly to skip FileResolver's init
        BaseResolver.__init__(self, *args, **kwargs)

        self.filepath = filepath

        # Set custom title if provided
        if title is not None:
            self.title = title

        # Override to hide file browser inputs
        self.hide_resolver_inputs = True

    def _on_file_chooser_path_changed(self, paths):
        # Override to prevent errors when file_chooser doesn't exist
        pass

    @observe('filepath')
    def _on_filepath_changed(self, change):
        # Simplified version that doesn't update UI widgets
        if not self.filepath:
            return
        self._resolver_input_updated()
        if not all(os.path.exists(p) for p in _as_path_list(self.filepath)):
            self.parsed_input_is_empty = True
