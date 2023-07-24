import os
from pathlib import Path

from glue_jupyter.common.toolbar_vuetify import read_icon
import ipyvuetify as v
from ipywidgets import jslink
from traitlets import List, Unicode, Dict, observe

from jdaviz import configs as jdaviz_configs
from jdaviz.cli import DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY, ALL_JDAVIZ_CONFIGS
from jdaviz.core.data_formats import identify_helper
from jdaviz.core.tools import ICON_DIR


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

    All other arguments are interpreted as load_data/load_spectrum arguments for
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
        return _launch_config_with_data(compatible_helpers[0], hdul, show, **kwargs)


def _launch_config_with_data(config, data=None, show=True, **kwargs):
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

    All other arguments are interpreted as load_data/load_spectrum arguments for
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
        viz_helper.load_data(data, **kwargs)

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

    # Define Icons
    cubeviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'cubeviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    specviz2d_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'specviz2d_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    mosviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'mosviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa
    imviz_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'imviz_icon.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, main, configs=ALL_JDAVIZ_CONFIGS, *args, **kwargs):
        self.main = main
        self.configs = configs
        # Set all configs to compatible at first load (for loading blank config)
        self.compatible_configs = configs

        self.config_icons = {
            'cubeviz': self.cubeviz_icon,
            'specviz': self.specviz_icon,
            'specviz2d': self.specviz2d_icon,
            'mosviz': self.mosviz_icon,
            'imviz': self.imviz_icon
        }
        
        self.loaded_data = None
        self.hint = "No filepath provided; will load blank tool"
        super().__init__(*args, **kwargs)

    @observe('filepath')
    def _filepath_changed(self, *args):
        self.hint = "Identifying file..."
        self.compatible_configs = []
        if self.filepath in (None, ''):
            self.compatible_configs = self.configs
            self.loaded_data = None
            self.hint = "No filepath provided; will load blank tool"
        else:
            path = Path(self.filepath)
            if not path.is_file():
                self.loaded_data = None
                self.hint = "Cannot find file on disk. Please check your filepath"
            else:
                try:
                    self.compatible_configs, self.loaded_data = identify_helper(self.filepath)
                    self.hint = "Compatible configs identified! Please select your config:"
                except Exception:
                    self.hint = "Could not autoidentify compatible config. Please manually select config to load your data into:"
                    self.compatible_configs = self.configs
                    self.loaded_data = self.filepath
                finally:
                    if len(self.compatible_configs) > 0 and self.loaded_data is None:
                        self.loaded_data = self.filepath
        # Clear hint if it's still stuck on "Identifying". We're in an ambiguous state
        self.hint = '' if self.hint == "Identifying file..." else self.hint

    def vue_launch_config(self, config):
        helper = _launch_config_with_data(config, self.loaded_data, show=False)
        self.main.children = [helper.app]

def show_launcher(configs=ALL_JDAVIZ_CONFIGS):
    main = v.Sheet(class_="mx-4", attributes={"id": "popout-widget-container"}, _metadata={'mount_id': 'content'})
    main.children = [Launcher(main, configs)]

    return main
