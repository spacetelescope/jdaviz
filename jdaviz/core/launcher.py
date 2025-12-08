import os

from astropy.io.registry.base import IORegistryError
from glue_jupyter.common.toolbar_vuetify import read_icon
import ipyvuetify as v
from ipywidgets import widget_serialization
from traitlets import List, Unicode, Dict, Bool, Any

from jdaviz import configs as jdaviz_configs
from jdaviz import __version__
from jdaviz.cli import DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY, ALL_JDAVIZ_CONFIGS
from jdaviz.core.data_formats import identify_helper
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.template_mixin import show_widget
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.utils import download_uri_to_path

STATUS_HINTS = {
    'idle': "Provide data using one of the resolvers below, or pick which viz tool to open",
    'identifying': "Identifying which tool is best to visualize your data...",
    'id ok': "The below tools can best visualize your data. Pick which one you want to use.",
    'id failed': "We couldn't identify which tool is best for your data. Pick a tool below to use."
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
    compatible_configs = List().tag(sync=True)
    config_icons = Dict().tag(sync=True)
    hint = Unicode().tag(sync=True)
    vdocs = Unicode("").tag(sync=True)  # App not available yet, so we need to recompute it here
    # Resolver Traitlets
    resolver_dialog_visible = Bool(False).tag(sync=True)
    active_resolver_tab = Unicode('file').tag(sync=True)
    active_resolver_widget = Any(None).tag(sync=True, **widget_serialization)
    resolver_items = List().tag(sync=True)

    # Define Icons
    cubeviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'cubeviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz2d_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz2d_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    mosviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'mosviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    imviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'imviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, main=None, configs=ALL_JDAVIZ_CONFIGS,
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

        # Ensure the file resolver starts in the current working directory
        os.environ['JDAVIZ_START_DIR'] = os.getcwd()

        # Don't create the temp app or resolvers yet - delay until first resolver is opened
        # This prevents any widgets from being created and auto-displayed
        self._temp_app = None
        self._resolver_classes = {}
        self._resolvers = {}
        self.resolver_items = []

        # Only include specific resolvers we want in the launcher
        resolver_names = ['file', 'file drop', 'url', 'virtual observatory']

        for name in resolver_names:
            if name in loader_resolver_registry.members:
                ResolverClass = loader_resolver_registry.members[name]
                self._resolver_classes[name] = ResolverClass
                self.resolver_items.append({
                    'name': name,
                    'label': name.title()
                })

        self.loaded_data = None
        self.hint = STATUS_HINTS['idle']

        super().__init__(*args, **kwargs)

    def _identify_data_from_resolver(self, resolver_name):
        """
        Use the active resolver to get data and identify compatible configs.
        """
        self.hint = STATUS_HINTS['identifying']
        self.compatible_configs = []

        resolver = self._resolvers.get(resolver_name)
        if resolver is None:
            self.hint = STATUS_HINTS['id failed']
            self.compatible_configs = self.configs
            return

        # Check if the resolver has valid input
        if not resolver.is_valid:
            self.compatible_configs = self.configs
            self.loaded_data = None
            self.hint = STATUS_HINTS['idle']
            return

        try:
            # Get the parsed input from the resolver
            parsed_input = resolver.parsed_input

            # Try to identify compatible helpers
            self.compatible_configs, self.loaded_data = identify_helper(parsed_input)
            self.hint = STATUS_HINTS['id ok']
        except Exception as e:
            print(f"Could not identify helper: {e}")
            self.hint = STATUS_HINTS['id failed']
            self.compatible_configs = self.configs
            self.loaded_data = resolver.parsed_input if resolver.is_valid else None

        # Clear hint if it's still stuck on "Identifying". We're in an ambiguous state
        self.hint = ('' if self.hint == STATUS_HINTS['identifying'] else self.hint)

    def vue_identify_data(self, event):
        """
        Called when the user wants to identify data from the active resolver.
        """
        resolver_name = event.get('resolver', self.active_resolver_tab)
        self._identify_data_from_resolver(resolver_name)
        # Close the dialog after identifying data
        self.resolver_dialog_visible = False

    def vue_open_resolver_dialog(self, event):
        """
        Opens the resolver dialog for the specified resolver.
        """
        resolver_name = event if isinstance(event, str) else event.get('resolver', 'file')
        self.active_resolver_tab = resolver_name

        # Ensure JDAVIZ_START_DIR is still set (in case something cleared it)
        if 'JDAVIZ_START_DIR' not in os.environ:
            os.environ['JDAVIZ_START_DIR'] = os.getcwd()

        # Create the temp app on first use if it doesn't exist yet
        if self._temp_app is None:
            from jdaviz.app import Application
            self._temp_app = Application(configuration='imviz')

        # Create the resolver on-demand if it doesn't exist yet
        if resolver_name not in self._resolvers and resolver_name in self._resolver_classes:
            try:
                ResolverClass = self._resolver_classes[resolver_name]
                resolver = ResolverClass(app=self._temp_app)
                self._resolvers[resolver_name] = resolver
            except Exception as e:
                print(f"Error creating resolver '{resolver_name}': {e}")
                import traceback
                traceback.print_exc()
                return

        # Set the active widget to be rendered in the dialog
        if resolver_name in self._resolvers:
            self.active_resolver_widget = self._resolvers[resolver_name]
        self.resolver_dialog_visible = True

    def vue_close_resolver_dialog(self, *args):
        """
        Closes the resolver dialog.
        """
        self.resolver_dialog_visible = False
        # Clear the active widget when closing
        self.active_resolver_widget = None

    def vue_launch_config(self, event):
        config = event.get('config')

        # Get the active resolver to load data
        resolver = self._resolvers.get(self.active_resolver_tab)
        data_to_load = self.loaded_data
        filepath_arg = None

        # If we have a valid resolver, try to use its output
        if resolver is not None and resolver.is_valid:
            try:
                # For file resolver, pass filepath as kwarg
                if self.active_resolver_tab == 'file':
                    filepath_arg = resolver.filepath
                data_to_load = resolver.parsed_input
            except Exception as e:
                print(f"Error getting data from resolver: {e}")

        # Launch the config with the data
        helper = _launch_config_with_data(config, data_to_load,
                                          filepath=filepath_arg, show=False)
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
        Deprecated. Previously used to autopopulate the file path field.

    height: int, optional
        The height of the top-level application widget, in pixels. Will be passed and processed
        by the selected configuration. Applies to the launcher and all instances of the same
        application in the notebook.
    '''
    # Color defined manually due to the custom theme not being defined yet (in main_styles.vue)
    height = f"{height}px" if isinstance(height, int) else height
    launcher = Launcher(None, configs, height)
    show_widget(launcher.main_with_launcher, loc='inline', title=None)
