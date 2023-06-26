import ipyvuetify as v
from ipywidgets import jslink

from jdaviz import configs as jdaviz_configs
from jdaviz.core.data_formats import identify_helper, _launch_config_with_data


def show_launcher(configs=['imviz', 'specviz', 'mosviz', 'cubeviz', 'specviz2d']):
    main = v.Sheet(class_="mx-4", _metadata={'mount_id': 'content'})
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
        config_btn.on_event('click', lambda btn, event, data: create_config(btn.children[0], loaded_data))
        btns[config] = config_btn

    # Create button row
    btn_row = v.Row()
    btn_row.children = list(btns.values())

    # Filepath row
    filepath_row = v.Row()
    text_field = v.TextField(label="File Path", v_model=None)

    def load_file(filepath):
        if filepath:
            helper, data_obj = identify_helper(filepath)
            for config, btn in btns.items():
                btn.disabled = not (config == helper)
                nonlocal loaded_data
                loaded_data = data_obj
            

    open_data_btn = v.Btn(class_="ma-2", outlined=True, color="primary",
                          children=[v.Icon(children=["mdi-upload"])])
    open_data_btn.on_event('click', lambda btn, event, data: load_file(btn.value))
    jslink((text_field, 'v_model'), (open_data_btn, 'value'))

    filepath_row.children = [text_field, open_data_btn]

    # Create Launcher
    main.children = [intro_row, filepath_row, btn_row]

    return main
