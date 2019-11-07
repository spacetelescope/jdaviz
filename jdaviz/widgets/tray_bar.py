import logging
import os

from traitlets import Unicode, List, Bool, Any

from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tray_bar.vue")) as f:
    TEMPLATE = f.read()


class TrayBar(TemplateMixin):
    """
    Application navigation drawer containing the lists of data and subsets
    currently in the glue collection.
    """
    template = Unicode(TEMPLATE).tag(sync=True)

    drawer = Bool(True).tag(sync=True)
    tab = Any(None).tag(sync=True)
    tray_items = List([]).tag(sync=True)
    app = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_tray(self, name, label=None, icon='save'):
        logging.info(f"Adding plugin {name} to tray bar.")
        self.tray_items.append({'name': name, 'label': label, 'icon': icon})

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass
