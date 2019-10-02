import ipyvuetify as v
from traitlets import Unicode, Bool
from .widgets.content_area import ContentArea
from .widgets.navigation_drawer import NavigationDrawer
from .widgets.toolbar import Toolbar
from glue.core.application_base import Application

from .config import tools


class IPyApplication(v.VuetifyTemplate):
    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_interact_drawer = Bool(True).tag(sync=True)

    template = Unicode("""
    <v-app id='glupyter'>
        <g-toolbar v-if="show_menu_bar" />
    </v-app>
    """).tag(sync=True)

    def __init__(self, *args, default_state=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._application_handler = Application()

        # Instantiate the default gui components
        self.components = {
            'g-toolbar': Toolbar(hub=self.hub),
            'g-interact-drawer': NavigationDrawer(hub=self.hub),
            'g-content-area': ContentArea(hub=self.hub)
        }

        if default_state is not None:
            self.show_menu_bar = default_state.get('menu_bar', True)
            self.show_toolbar = default_state.get('toolbar', True)
            self.show_interact_drawer = default_state.get('iteract_drawer', True)

        # Dump all user-defined toolbar items as component references in the
        # vuetify template instance.
        toolbar = self.components.get('g-toolbar')

        toolbar.components = {k: v(hub=self.hub)
                              for k, v in tools.members.items()}

        # Do the same fo the menu bar items
        # menu_bar = self.components.get('g-menu-bar')
        # menu_bar.components = {k: v(hub=self.hub) 
        #                        for k, v in menus.members.items()}

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    def load_configuration(self):
        for name in tools.members:
            self.components['g-toolbar'].append(name)
