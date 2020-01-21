import logging
import os

from traitlets import Unicode, List, Bool, Any, Float, Int, observe

from jdaviz.core.template_mixin import TemplateMixin

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

    methods = Unicode("""
    {
        checkNotebookContext() {
            this.notebook_context = !!!document.getElementById("web-app");
            return this.notebook_context;
        }
    }
    """).tag(sync=True)

    def vue_tab_changed(self, index):
        self.mini = isinstance(index, dict)

    def vue_fixed_tray_items(self, *args, **kwargs):
        return [x for x in self.tray_items if x.get('name') not in
                ('g-data-collection-list', 'g-viewer-options', 'g-layer-options')]

    def add_tray(self, name, label=None, icon='save'):
        print(f"Adding plugin {name} to tray bar.")

        self.tray_items.append({'name': name, 'label': label, 'icon': icon})
