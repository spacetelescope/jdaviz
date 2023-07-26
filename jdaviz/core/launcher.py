import ipyvuetify as v
from ipywidgets import jslink

from jdaviz import configs as jdaviz_configs
from jdaviz.cli import DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY, ALL_JDAVIZ_CONFIGS
from jdaviz.core.data_formats import identify_helper


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


def show_launcher(configs=['imviz', 'specviz', 'mosviz', 'cubeviz', 'specviz2d']):
    main = v.Sheet(
        class_="mx-4",
        attributes={"id": "popout-widget-container"},
        _metadata={'mount_id': 'content'})
    main.children = []

    # Create Intro Row
    intro_row = v.Row()
    welcome_text = v.Html(tag='h1', attributes={'title': 'a title'},
                          children=['Welcome to Jdaviz'])
    intro_row.children = [welcome_text]

    # Config buttons
    def create_config(config, data=None):
        helper = _launch_config_with_data(config, data, show=False)
        main.children = [helper.app]

    btns = {}
    loaded_data = None
    for config in configs:
        config_btn = v.Btn(class_="ma-2", outlined=True, color="primary",
                           children=[config.capitalize()])
        config_btn.on_event('click', lambda btn, event, data: create_config(btn.children[0],
                                                                            loaded_data))
        btns[config] = config_btn

    # Create button row
    btn_row = v.Row()
    btn_row.children = list(btns.values())

    # Filepath row
    filepath_row = v.Row()
    text_field = v.TextField(label="File Path", v_model=None)

    def enable_compatible_configs(filepath):
        nonlocal loaded_data
        if filepath in (None, ''):
            compatible_helpers = ALL_JDAVIZ_CONFIGS
            loaded_data = None
        else:
            compatible_helpers, loaded_data = identify_helper(filepath)
            if len(compatible_helpers) > 0 and loaded_data is None:
                loaded_data = filepath

        for config, btn in btns.items():
            btn.disabled = not (config in compatible_helpers)

    id_data_btn = v.Btn(class_="ma-2", outlined=True, color="primary",
                        children=[v.Icon(children=["mdi-magnify"])])
    id_data_btn.on_event('click', lambda btn, event, data: enable_compatible_configs(btn.value))
    jslink((text_field, 'v_model'), (id_data_btn, 'value'))

    filepath_row.children = [text_field, id_data_btn]

    # Create Launcher
    main.children = [intro_row, filepath_row, btn_row]

    return main
