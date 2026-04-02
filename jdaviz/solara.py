import os
from pathlib import Path
import threading

import solara
import solara.lab
import ipygoldenlayout
import ipysplitpanes
import ipyvue
import ipyvuetify

import jdaviz
from jdaviz.app import custom_components

config = None
data_list = []
format_list = []
load_data_kwargs = {}
jdaviz_verbosity = 'error'
jdaviz_history_verbosity = 'info'


@solara.lab.on_kernel_start
def on_kernel_start():
    print("Starting kernel", solara.get_kernel_id())
    # at import time, solara runs with a dummy kernel
    # we simply ignore that
    if "dummy" in solara.get_kernel_id():
        return

    def on_kernel_close():
        def exit_process():
            # sys.exit(0) does not work, it just throws an exception
            # this really makes the process exit
            os._exit(0)
        # give the kernel some time to close
        threading.Thread(target=exit_process).start()
    return on_kernel_close


def create_shared_widgets():
    ipysplitpanes.SplitPanes()
    ipygoldenlayout.GoldenLayout()
    for name, path in custom_components.items():
        ipyvue.register_component_from_file(None, name,
                                            os.path.join(os.path.dirname(jdaviz.__file__), path))

    ipyvue.register_component_from_file('g-viewer-tab', "container.vue", jdaviz.__file__)


def get_app_or_launcher():
    '''
    Return either the app instance or the launcher page as appropriate
    '''
    main = ipyvuetify.Sheet(class_="mx-25",
                 attributes={"id": "popout-widget-container"},
                 color="#00212C",
                 height='100vh')

    if config is None or not hasattr(jdaviz.configs, config):
        if config == 'Flexible':
            viz = jdaviz.gca()
            if not len(data_list):
                jdaviz.loaders['file'].open_in_tray()
            else:
                with jdaviz.batch_load():
                    for filename, format in zip(data_list, format_list):
                        jdaviz.load(filename, format=format)
        else:
            from jdaviz.core.launcher import Launcher
            launcher = Launcher(main=main, height='100vh',
                                filepath=(data_list[0] if len(data_list) == 1 else ''))
            return launcher.main_with_launcher

    else:
        viz = getattr(jdaviz.configs, config)(verbosity=jdaviz_verbosity,
                                              history_verbosity=jdaviz_history_verbosity)
        for data in data_list:
            if config == 'Mosviz':
                viz.load(directory=data, **load_data_kwargs)
            else:
                viz.load(data, **load_data_kwargs)

    main.color = 'transparent'
    main.children = [viz.app]
    return main

def Jdaviz():
    # Create the shared widgets, using use_memo to ensure we only do it once
    solara.use_memo(create_shared_widgets, [])

    app_or_launcher = solara.use_memo(get_app_or_launcher, [config, data_list, format_list])

    #return app_or_launcher
    return solara.Column(children=[app_or_launcher])

@solara.component
def Page():
    if config is None:
        solara.Text("No config defined")
        return

    solara.Style(Path(__file__).parent / "solara.css")

    solara.Title("Jdaviz")
    # solara.display(Jdaviz())
    return Jdaviz()
