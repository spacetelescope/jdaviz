import os
from pathlib import Path
import signal

import solara
import solara.lab
import ipygoldenlayout
import ipysplitpanes
import ipyvue

import jdaviz
from jdaviz.app import custom_components

config = None
data_list = []
load_data_kwargs = {}
jdaviz_verbosity = 'error'
jdaviz_history_verbosity = 'info'


@solara.lab.on_kernel_start
def on_kernel_start():
    # at import time, solara runs with a dummy kernel
    # we simply ignore that
    if "dummy" in solara.get_kernel_id():
        return

    def on_kernel_close():
        # for some reason, sys.exit(0) does not work here
        # see https://github.com/encode/uvicorn/discussions/1103
        signal.raise_signal(signal.SIGINT)
    return on_kernel_close


@solara.component
def Page():
    solara.Title("Jdaviz")

    if config is None:
        solara.Text("No config defined")
        return

    ipysplitpanes.SplitPanes()
    ipygoldenlayout.GoldenLayout()
    for name, path in custom_components.items():
        ipyvue.register_component_from_file(None, name,
                                            os.path.join(os.path.dirname(jdaviz.__file__), path))

    ipyvue.register_component_from_file('g-viewer-tab', "container.vue", jdaviz.__file__)

    solara.Style(Path(__file__).parent / "solara.css")

    if config is None or not hasattr(jdaviz.configs, config):
        from jdaviz.core.launcher import Launcher
        launcher = Launcher(height='100vh', filepath=(data_list[0] if len(data_list) == 1 else ''))
        solara.display(launcher.main_with_launcher)
        return

    viz = getattr(jdaviz.configs, config)(verbosity=jdaviz_verbosity,
                                          history_verbosity=jdaviz_history_verbosity)
    for data in data_list:
        if config == 'mosviz':
            viz.load_data(directory=data, **load_data_kwargs)
        else:
            viz.load_data(data, **load_data_kwargs)

    solara.display(viz.app)
