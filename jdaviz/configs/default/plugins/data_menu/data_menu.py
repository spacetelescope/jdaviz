from traitlets import Dict, Unicode

from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.user_api import UserApiWrapper
from jdaviz.core.events import IconsUpdatedMessage

__all__ = ['DataMenu']


class DataMenu(TemplateMixin):
    """Viewer Data Menu"""
    template_file = __file__, "data_menu.vue"

    viewer_id = Unicode().tag(sync=True)
    viewer_reference = Unicode().tag(sync=True)

    layer_icons = Dict().tag(sync=True)  # read-only, see app.state.layer_icons
    viewer_icons = Dict().tag(sync=True)  # read-only, see app.state.viewer_icons

    visible_layers = Dict().tag(sync=True)  # read-only, set by viewer

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer = viewer
        # first attach callback to catch any updates to viewer/layer icons and then
        # set their initial state
        self.hub.subscribe(self, IconsUpdatedMessage, self._on_app_icons_updated)
        self.viewer_icons = dict(self.app.state.viewer_icons)
        self.layer_icons = dict(self.app.state.layer_icons)

    @property
    def user_api(self):
        expose = []
        return UserApiWrapper(self, expose=expose)

    def set_viewer_id(self):
        # viewer_ids are not populated on the viewer at init, so we'll keep checking and set
        # these the first time that they are available
        if len(self.viewer_id) and len(self.viewer_reference):
            return
        try:
            self.viewer_id = getattr(self._viewer, '_reference_id', '')
            self.viewer_reference = self._viewer.reference
        except AttributeError:
            return

    def _on_app_icons_updated(self, msg):
        if msg.icon_type == 'viewer':
            self.viewer_icons = msg.icons
        elif msg.icon_type == 'layer':
            self.layer_icons = msg.icons
        self.set_viewer_id()
