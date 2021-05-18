
import pathlib
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from jdaviz.core.events import DataPromptMessage
from traitlets import Unicode, Bool, observe, List
from jdaviz.core.registries import component_registry

__all__ = ['DataPrompt']


@component_registry('data-prompt')
class DataPrompt(TemplateMixin):
    template = load_template("data_prompt.vue", __file__).tag(sync=True)
    status_msg = Unicode("").tag(sync=True)
    status = Unicode("").tag(sync=True)
    filename = Unicode("").tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    products = List().tag(sync=True)
    configs = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataPromptMessage,
                           handler=self._on_status_updated)

    def _on_status_updated(self, msg):
        self.status_msg = msg.status
        self.status = ('success' if 'Success' in msg.status else 'error'
                       if 'Error' in msg.status else 'unknown')
        self.filename = str(pathlib.Path(msg.filename).stem)

        self.products = [{"title": "Mission", "subtitle": msg.header.get('TELESCOP')},
                         {"title": "Instrument", "subtitle": msg.header.get('INSTRUME')},
                         {"title": "Exposure Type", "subtitle": msg.header.get('EXP_TYPE')},
                         {"title": "Template", "subtitle": msg.header.get('TEMPLATE')}]

        self.configs = [{"title": "Data Format", "subtitle": msg.data_format},
                        {"title": "Current Config", "subtitle": msg.current},
                        {"title": "Suggested Format", "subtitle": msg.suggested_format},
                        {"title": "Suggested Config", "subtitle": msg.suggested_config},
                        {"title": "Config", "subtitle": msg.config}]

    @observe("status_msg")
    def _on_status_changed(self, event):
        old_status = event['old']
        new_status = event['new']
        if new_status and new_status != old_status:
            self.status = new_status
            self.dialog = True

    def vue_close(self, *args, **kwargs):
        self.status = ''
        self.load = False
        self.dialog = False
