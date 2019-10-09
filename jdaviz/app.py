import os

import ipyvuetify as v
import yaml
from glue.core.application_base import Application, HubListener
from glue_jupyter.app import JupyterApplication
from traitlets import Unicode, Bool, Dict

from jdaviz.core.registries import tools, trays
from .widgets.content_area import ContentArea
from .widgets.toolbar import Toolbar
from .widgets.tray_bar import TrayBar
from .core.events import NewViewerMessage, AddViewerMessage, LoadDataMessage

from glue_jupyter.bqplot.profile import BqplotProfileView


class IPyApplication(v.VuetifyTemplate, HubListener):
    _metadata = Dict({'mount_id': 'content'}).tag(sync=True)

    show_menu_bar = Bool(True).tag(sync=True)
    show_toolbar = Bool(True).tag(sync=True)
    show_tray_bar = Bool(True).tag(sync=True)

    template = Unicode("""
    <v-app id='glupyter'>
        <g-toolbar v-if="show_toolbar" />
        <g-tray-bar v-if="show_tray_bar" />
        <g-content-area />
    </v-app>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: we shouldn't need to keep an entire JupyterApplication
        #  instance, however, there are certain things on the glupyter viewers
        #  that reference custom functionality in this class. Eventually, we
        #  should parse those out so they aren't dependencies.
        self._application_handler = JupyterApplication()

        # Instantiate the default gui components
        self.components = {
            'g-toolbar': Toolbar(session=self.session),
            'g-tray-bar': TrayBar(session=self.session),
            'g-content-area': ContentArea(session=self.session)
        }

        # Dump all user-defined toolbar items as component references in the
        #  vuetify template instance.
        toolbar = self.components.get('g-toolbar')
        toolbar.components = {k: v(session=self.session)
                              for k, v in tools.members.items()}

        # Do the same thing for the sidebar components
        tray_bar = self.components.get('g-tray-bar')
        tray_bar.components = {k: v(session=self.session)
                               for k, v in trays.members.items()}

        # Load in default configuration file
        self.load_configuration()

        # Setup hub event listeners
        self.hub.subscribe(self, NewViewerMessage,
                           handler=self._on_new_viewer)
        self.hub.subscribe(self, LoadDataMessage,
                           handler=self._on_load_data)

        # -- Test

        # data = self._application_handler.load_data("/Users/nearl/data/single_g235h-f170lp_x1d.fits")
        # new_viewer_msg = NewViewerMessage(BqplotProfileView, data[0], sender=self)
        # self.hub.broadcast(new_viewer_msg)
        # self.hub.broadcast(new_viewer_msg)

        # --

    @property
    def hub(self):
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        return self._application_handler.session

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

    def _on_load_data(self, msg):
        data = self._application_handler.load_data(msg.path)
        new_viewer_msg = NewViewerMessage(BqplotProfileView, data[0], sender=self)
        self.hub.broadcast(new_viewer_msg)

    def _on_new_viewer(self, msg):
        view = self._application_handler.new_data_viewer(msg.cls,
                                                         data=msg.data,
                                                         show=False
                                                         )

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            view.state.x_att = x

        self.hub.broadcast(AddViewerMessage(view, sender=self))

        return view
