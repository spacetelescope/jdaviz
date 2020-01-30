import logging
import os

from traitlets import Unicode, List, Bool, Any, Float, Int

from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "tray_bar.vue")) as f:
    TEMPLATE = f.read()


class TrayBar(TemplateMixin):
    """
    Application navigation drawer containing the lists of data and subsets
    currently in the glue collection.
    """
    tab = Any(0).tag(sync=True)
    template = Unicode(TEMPLATE).tag(sync=True)
    drawer = Bool(True).tag(sync=True)
    tray_items = List([]).tag(sync=True)
    app = Bool(True).tag(sync=True)
    mini = Bool(False).tag(sync=True)

    css = Unicode("""
    .v-tabs--vertical > .v-tabs-bar .v-tab {
        min-width: 49px;
    }
    """).tag(sync=True)

    def vue_tab_changed(self, index):
        self.mini = isinstance(index, dict)

    def add_tray(self, name, label=None, icon='save'):
        logging.info(f"Adding plugin {name} to tray bar.")

        self.tray_items.append({'name': name, 'label': label, 'icon': icon})
