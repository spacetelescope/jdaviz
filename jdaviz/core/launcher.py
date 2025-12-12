import os
from pathlib import Path

from astropy.io.registry.base import IORegistryError
from glue_jupyter.common.toolbar_vuetify import read_icon
import ipyvuetify as v
from traitlets import List, Unicode, Dict, Bool, observe, Any
from ipywidgets import widget_serialization
from solara import FileBrowser, reactive
import reacton

from jdaviz import configs as jdaviz_configs
from jdaviz import __version__
from jdaviz.cli import DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY, ALL_JDAVIZ_CONFIGS
from jdaviz.core.data_formats import identify_helper
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.template_mixin import show_widget
from jdaviz.utils import download_uri_to_path

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
    # first catch URIs and download them, or return filename unchanged:
    if "local_path" in kwargs:
        fn_dl_kw = {"local_path": kwargs["local_path"]}
    else:
        fn_dl_kw = {}
    filename = download_uri_to_path(filename, cache=True, **fn_dl_kw)

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
        A filepath or Jdaviz-compatible data object (such as Spectrum or CCDData)
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
    file_browser_widget = Any(None).tag(sync=True, **widget_serialization)
    file_browser_visible = Bool(False).tag(sync=True)

    # Define Icons
    cubeviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'cubeviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz2d_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz2d_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    mosviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'mosviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    imviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'imviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, main=None, configs=ALL_JDAVIZ_CONFIGS, filepath='',
                 height=None, *args, **kwargs):
        self.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

        if main is None:
            main = v.Sheet(class_="mx-25",
                           attributes={"id": "popout-widget-container"},
                           color="#00212C",
                           height=height)

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

        self.file_browser_widget = None
        self.file_browser_dir = None
        self.selected_file = None
        self.components = {}
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

    def _create_file_browser(self):
        if self.file_browser_widget is None:
            # Ensure JDAVIZ_START_DIR is set to absolute path of current working directory
            if 'JDAVIZ_START_DIR' not in os.environ:
                os.environ['JDAVIZ_START_DIR'] = os.path.abspath(os.getcwd())

            start_path = Path(os.path.abspath(os.environ['JDAVIZ_START_DIR']))
            self.file_browser_dir = reactive(start_path)
            self.selected_file = reactive('')
            self.file_browser_widget_el = FileBrowser(
                directory=self.file_browser_dir,
                selected=self.selected_file,
                on_path_select=self._on_file_select,
                can_select=True
            )
            self.file_browser_widget, rc = reacton.render(self.file_browser_widget_el)

    def _on_file_select(self, path):
        # don't set filepath here, only set it when user clicks Import button
        pass

    def vue_open_file_dialog(self, *args, **kwargs):
        self._create_file_browser()
        self.file_browser_visible = True

    def vue_choose_file(self, *args, **kwargs):
        if self.selected_file is not None and self.selected_file.value:
            full_path = os.path.join(self.file_browser_dir.value, self.selected_file.value)
            self.filepath = full_path
        self.file_browser_visible = False

    def vue_launch_config(self, event):
        config = event.get('config')
        helper = _launch_config_with_data(config, self.loaded_data,
                                          filepath=self.filepath, show=False)
        if self.height not in ['100%', '100vh']:
            # We're in jupyter mode. Set to default height
            default_height = helper.app.state.settings['context']['notebook']['max_height']
            helper.app.layout.height = default_height
            self.main.height = default_height
        self.main.color = 'transparent'
        self.main.children = [helper.app]

    @property
    def main_with_launcher(self):
        self.main.children = [self]
        return self.main


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
    # Color defined manually due to the custom theme not being defined yet (in main_styles.vue)
    height = f"{height}px" if isinstance(height, int) else height
    launcher = Launcher(None, configs, filepath, height)
    show_widget(launcher.main_with_launcher, loc='inline', title=None)
