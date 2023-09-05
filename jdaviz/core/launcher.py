import os
from pathlib import Path

from astropy.io.registry.base import IORegistryError
from glue_jupyter.common.toolbar_vuetify import read_icon
import ipyvuetify as v
from traitlets import List, Unicode, Dict, Bool, observe

from jdaviz import configs as jdaviz_configs
from jdaviz import __version__
from jdaviz.cli import DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY, ALL_JDAVIZ_CONFIGS
from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.data_formats import identify_helper
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.template_mixin import show_widget

STATUS_HINTS = {
    'idle': "Provide a file path, or pick which viz tool to open",
    'identifying': "Identifying which tool is best to visualize your file...",
    'invalid path': "Error: Cannot find file. Please check your file path.",
    'id ok': "The below tools can best visualize your file. Pick which one you want to use.",
    'id failed': "We couldn’t identify which tool is best for your file. Pick a tool below to use."

}


def open(filename, show=True, **kwargs):
    '''
    Automatically detect the correct configuration based on a given file,
    load the data, and display the configuration

    Parameters
    ----------
    filename : str (path-like)
        Name for a local data file.
    show : bool
        Determines whether to immediately show the application

    All other arguments are interpreted as load_data arguments for
    the autoidentified configuration class

    Returns
    -------
    Jdaviz ConfigHelper : jdaviz.core.helpers.ConfigHelper
        The autoidentified ConfigHelper for the given data
    '''
    # Identify the correct config
    compatible_helpers, hdul = identify_helper(filename)
    if len(compatible_helpers) > 1:
        raise NotImplementedError(f"Multiple helpers provided: {compatible_helpers}."
                                  "Unsure which to launch")
    else:
        return _launch_config_with_data(compatible_helpers[0], hdul, filepath=filename,
                                        show=show, **kwargs)


def _launch_config_with_data(config, data=None, show=True, filepath=None, **kwargs):
    '''
    Launch jdaviz with a specific, known configuration and data

    Parameters
    ----------
    config : str (path-like)
        Name for a local data file.
    data : str or any Jdaviz-compatible data
        A filepath or Jdaviz-compatible data object (such as Spectrum1D or CCDData)
    show : bool
        Determines whether to immediately show the application
    filepath : str
        Filepath to use as fallback if ``data`` fails to load.

    All other arguments are interpreted as load_data arguments for
    the autoidentified configuration class

    Returns
    -------
    Jdaviz ConfigHelper : jdaviz.core.helpers.ConfigHelper
        The loaded ConfigHelper with data loaded
    '''
    viz_class = getattr(jdaviz_configs, config.capitalize())

    # Create config instance
    verbosity = kwargs.pop('verbosity', DEFAULT_VERBOSITY)
    history_verbosity = kwargs.pop('history_verbosity', DEFAULT_HISTORY_VERBOSITY)
    viz_helper = viz_class(verbosity=verbosity, history_verbosity=history_verbosity)

    # Load data
    if data not in (None, ''):
        try:
            viz_helper.load_data(data, **kwargs)
        except IORegistryError:
            if filepath is None:
                raise
            viz_helper.load_data(filepath, **kwargs)

    # Display app
    if show:
        viz_helper.show()

    return viz_helper


class Launcher(v.VuetifyTemplate):
    template_file = __file__, "launcher.vue"
    configs = List().tag(sync=True)
    filepath = Unicode().tag(sync=True)
    compatible_configs = List().tag(sync=True)
    config_icons = Dict().tag(sync=True)
    hint = Unicode().tag(sync=True)
    vdocs = Unicode("").tag(sync=True)  # App not available yet, so we need to recompute it here
    # File picker Traitlets
    error_message = Unicode().tag(sync=True)
    valid_path = Bool(True).tag(sync=True)
    file_chooser_visible = Bool(False).tag(sync=True)

    # Define Icons
    cubeviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'cubeviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz2d_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz2d_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    mosviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'mosviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    imviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'imviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, main, configs=ALL_JDAVIZ_CONFIGS, filepath='', height=None, *args, **kwargs):
        self.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

        self.main = main
        self.configs = configs
        self.height = f"{height}px" if isinstance(height, int) else height
        # Set all configs to compatible at first load (for loading blank config)
        self.compatible_configs = configs

        self.config_icons = {
            'cubeviz': self.cubeviz_icon,
            'specviz': self.specviz_icon,
            'specviz2d': self.specviz2d_icon,
            'mosviz': self.mosviz_icon,
            'imviz': self.imviz_icon
        }

        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_chooser = FileChooser(start_path)
        self.components = {'g-file-import': self._file_chooser}
        self.loaded_data = None
        self.hint = STATUS_HINTS['idle']

        self.filepath = filepath

        super().__init__(*args, **kwargs)

    @observe('filepath')
    def _filepath_changed(self, *args):
        self.hint = STATUS_HINTS['identifying']
        self.compatible_configs = []
        if self.filepath in (None, ''):
            self.compatible_configs = self.configs
            self.loaded_data = None
            self.hint = STATUS_HINTS['idle']
        else:
            path = Path(self.filepath)
            if not path.is_file():
                self.loaded_data = None
                self.hint = STATUS_HINTS['invalid path']
            else:
                try:
                    self.compatible_configs, self.loaded_data = identify_helper(self.filepath)
                    self.hint = STATUS_HINTS['id ok']
                except Exception:
                    self.hint = STATUS_HINTS['id failed']
                    self.compatible_configs = self.configs
                    self.loaded_data = self.filepath
                finally:
                    if len(self.compatible_configs) > 0 and self.loaded_data is None:
                        self.loaded_data = self.filepath
        # Clear hint if it's still stuck on "Identifying". We're in an ambiguous state
        self.hint = ('' if self.hint == STATUS_HINTS['identifying'] else self.hint)

    def vue_choose_file(self, *args, **kwargs):
        if self._file_chooser.file_path is None:
            self.error_message = "No file selected"
        elif Path(self._file_chooser.file_path).is_file():
            self.file_chooser_visible = False
            self.filepath = self._file_chooser.file_path

    def vue_launch_config(self, event):
        config = event.get('config')
        helper = _launch_config_with_data(config, self.loaded_data,
                                          filepath=self.filepath, show=False)
        if self.height != '100%':
            # We're in jupyter mode. Set to default height
            default_height = helper.app.state.settings['context']['notebook']['max_height']
            helper.app.layout.height = default_height
            self.main.height = default_height
        self.main.color = 'transparent'
        self.main.children = [helper.app]


def show_launcher(configs=ALL_JDAVIZ_CONFIGS, filepath='', height='450px'):
    '''Display an interactive Jdaviz launcher to select your data and compatible configuration

    Parameters
    ----------
    filepath: str, optional
        The path to the file to load into Jdaviz. Will autopopulate the File Path field

    height: int, optional
        The height of the top-level application widget, in pixels. Will be passed and processed
        by the selected configuration. Applies to the launcher and all instances of the same
        application in the notebook.
    '''
    # Color defined manually due to the custom theme not being defined yet (in app.vue)
    height = f"{height}px" if isinstance(height, int) else height
    main = v.Sheet(class_="mx-25",
                   attributes={"id": "popout-widget-container"},
                   color="#00212C",
                   height=height,
                   _metadata={'mount_id': 'content'})
    main.children = [Launcher(main, configs, filepath, height)]

    show_widget(main, loc='inline', title=None)
