import ipyvuetify as v
from ipywidgets import jslink
from traitlets import Dict

from jdaviz import configs as jdaviz_configs
from jdaviz.core.data_formats import open as jdaviz_open


def show_launcher(configs=['imviz', 'specviz', 'mosviz', 'cubeviz', 'specviz2d']):
    main = v.Sheet(class_="mx-4", _metadata={'mount_id': 'content'})
    main.children = []

    # Create Intro Row
    intro_row = v.Row()
    welcome_text = v.Html(tag='h1', attributes={'title': 'a title'},
                          children=['Welcome to Jdaviz'])
    intro_row.children = [welcome_text]

    # Filepath row
    filepath_row = v.Row()
    text_field = v.TextField(label="File Path", v_model=None)

    def load_file(filepath):
        if filepath:
            helper = jdaviz_open(filepath, show=False)
            main.children = [helper.app]

    open_data_btn = v.Btn(class_="ma-2", outlined=True, color="primary",
                          children=[v.Icon(children=["mdi-upload"])])
    open_data_btn.on_event('click', lambda btn, event, data: load_file(btn.value))
    jslink((text_field, 'v_model'), (open_data_btn, 'value'))

    filepath_row.children = [text_field, open_data_btn]

    # Config buttons
    def create_config(config):
        viz_class = getattr(jdaviz_configs, config.capitalize())
        main.children = [viz_class().app]

    btns = []
    for config in configs:
        config_btn = v.Btn(class_="ma-2", outlined=True, color="primary",
                           children=[config.capitalize()])
        config_btn.on_event('click', lambda btn, event, data: create_config(btn.children[0]))
        btns.append(config_btn)

    # Create button row
    btn_row = v.Row()
    btn_row.children = btns
    main.children = [intro_row, filepath_row, btn_row]

    return main
