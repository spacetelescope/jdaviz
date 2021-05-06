
import pathlib
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from jdaviz.core.events import SnackbarMessage, DataPromptMessage
from traitlets import Unicode, Bool, observe, Dict, Int, Float, default, Union
from jdaviz.core.registries import component_registry
from astropy.io.fits import Header
import json

__all__ = ['DataPrompt']


@component_registry('data-prompt')
class DataPrompt(TemplateMixin):
    template = load_template("data_prompt.vue", __file__).tag(sync=True)
    status_msg = Unicode("").tag(sync=True)
    status = Unicode("").tag(sync=True)
    filename = Unicode("").tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    load = Bool(False).tag(sync=True)
    error_message = Unicode().tag(sync=True)
    config = Unicode("Unknown").tag(sync=True)
    data_format = Unicode("Unknown").tag(sync=True)
    current = Unicode("Unknown").tag(sync=True)
    suggested_format = Unicode("Unknown").tag(sync=True)
    suggested_config = Unicode("Unknown").tag(sync=True)
    header = Dict(Union([Unicode("Unknown"), Bool(None), Int(-9999), Float(-9999)]) ).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataPromptMessage,
                           handler=self._on_status_updated)

    def _on_status_updated(self, msg):
        self.status_msg = msg.status
        self.status = 'success' if 'Success' in msg.status else 'error' if 'Error' in msg.status else 'unknown'
        self.config = msg.config
        self.data_format = msg.data_format
        self.current = msg.current
        self.suggested_format = msg.suggested_format
        self.suggested_config = msg.suggested_config
        self.filename = str(pathlib.Path(msg.filename).stem)

        self.header = msg.header

    @observe("status_msg")
    def _on_status_changed(self, event):
        old_status = event['old']
        new_status = event['new']
        print('event', event)
        if new_status and new_status != old_status:
            print('updating status')
            self.status = new_status
            self.dialog = True

    @observe("load")
    def _update_data_load_state(self, event):
        print('updating loading')
        self.app.state.data_prompt['dialog'] = False
        self.app.state.data_prompt['load'] = event['new']
        self.app.state.data_prompt['status'] = ''
        print('new load', self.app.state.data_prompt.get('load', ''))

    def vue_close(self, *args, **kwargs):
        print('close', self.app.state.data_prompt.get('status', ''),
              self.app.state.data_prompt.get('dialog', ''))
        self.status = ''
        self.load = False
        self.dialog = False

    def vue_load_data(self, *args, **kwargs):
        print('load', self.app.state.data_prompt.get('status', ''),
              self.app.state.data_prompt.get('dialog', ''))
        snack = SnackbarMessage(self.status, sender=self, color='error')
        self.hub.broadcast(snack)
        self.load = True
        self.dialog = False
