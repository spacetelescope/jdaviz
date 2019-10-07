import os

import ipyvuetify as v
import yaml
from glue.core.application_base import Application
from traitlets import Unicode, Bool, Dict

from jdaviz.core.registries import tools, trays
from .widgets.content_area import ContentArea
from .widgets.toolbar import Toolbar
from .widgets.tray_bar import TrayBar


class IPyApplication(v.VuetifyTemplate, Application):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_tray_bar = Bool(True).tag(sync=True)

    template = Unicode("""
    <v-app id='glupyter'>
        <g-toolbar v-if="show_menu_bar" />
        <g-tray-bar />
        <g-content-area />
    </v-app>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._application_handler = Application()

        # Instantiate the default gui components
        self.components = {
            'g-toolbar': Toolbar(hub=self.hub),
            'g-tray-bar': TrayBar(hub=self.hub),
            'g-content-area': ContentArea(hub=self.hub)
        }

        # Dump all user-defined toolbar items as component references in the
        # vuetify template instance.
        toolbar = self.components.get('g-toolbar')
        toolbar.components = {k: v(hub=self.hub)
                              for k, v in tools.members.items()}

        # Do the same thing for the sidebar components
        tray_bar = self.components.get('g-tray-bar')
        tray_bar.components = {k: v(hub=self.hub)
                               for k, v in trays.members.items()}

        self.load_configuration()

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    def load_configuration(self):
        # Parse the default configuration file
        path = os.path.join(
            os.path.dirname(__file__),
            "configs",
            "default",
            "default.yaml")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # Get a reference to the component visibility states
        comps = config.get('components', {})

        # Toggle the rendering of the components in the gui
        self.show_menu_bar = comps.get('menu_bar', True)
        self.show_toolbar = comps.get('toolbar', True)
        self.show_tray_bar = comps.get('iteract_drawer', True)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            self.components['g-toolbar'].add_tool(name)

        # Add the tray items filter to the interact drawer component
        for name in config.get('tray_bar', []):
            self.components['g-tray-bar'].add_tray(name)
