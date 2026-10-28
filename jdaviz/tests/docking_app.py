"""Real image viewers for the Python Playwright docking smoke test."""

import json

import ipyvuetify
import numpy as np
import solara
from traitlets import Unicode

from jdaviz import Imviz
from jdaviz.solara import create_shared_widgets


def create_app():
    create_shared_widgets()
    helper = Imviz()
    helper.load_data(np.arange(1024).reshape(32, 32), data_label='test image')
    app = helper._app
    helper.create_image_viewer(viewer_name='comparison')
    app.add_data_to_viewer('comparison', 'test image')
    viewers = dict(app._viewer_store)
    widgets = {item['id']: item['widget'] for item in app.state.viewer_items}

    class LayoutProbe(ipyvuetify.VuetifyTemplate):
        status = Unicode('').tag(sync=True)
        template = Unicode('''<template><div>
          <button id="inspect-layout" @click="inspect">Inspect layout</button>
          <pre id="layout-status">{{ status }}</pre>
        </div></template>''').tag(sync=True)

        def vue_inspect(self, *_):
            self._inspection = getattr(self, '_inspection', 0) + 1
            self.status = json.dumps({
                'inspection': self._inspection,
                'layout': app.state.viewer_layout,
                'ids': list(app._viewer_store),
                'same_viewers': all(viewers[vid] is viewer
                                    for vid, viewer in app._viewer_store.items()),
                'same_widgets': all(widgets[item['id']] == item['widget']
                                    for item in app.state.viewer_items),
            })

    return app, LayoutProbe()


@solara.component
def Page():
    fixture, set_fixture = solara.use_state(None)
    # Construct widgets after rendering, as the main Jdaviz Solara page does.
    solara.use_effect(lambda: set_fixture(create_app()), [])
    if fixture is not None:
        app, probe = fixture
        solara.display(probe)
        solara.display(app)
