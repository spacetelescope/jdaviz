from traitlets import Dict, Unicode

from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.user_api import UserApiWrapper

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
        self.app.state.add_callback('viewer_icons', self._on_app_viewer_icons_changed)
        self.app.state.add_callback('layer_icons', self._on_app_layer_icons_changed)
        self._on_app_viewer_icons_changed(self.app.state.viewer_icons)
        self._on_app_layer_icons_changed(self.app.state.layer_icons)

    @property
    def user_api(self):
        expose = []
        return UserApiWrapper(self, expose=expose)

    def set_viewer_id(self):
        # TODO: refactor so this can be set once
        try:
            self.viewer_id = getattr(self._viewer, '_reference_id', '')
            self.viewer_reference = self._viewer.reference
        except Exception:
            pass

    def _on_app_viewer_icons_changed(self, value):
        # value is a CallbackDict, cast to dict
        self.viewer_icons = dict(value)
        self.set_viewer_id()

    def _on_app_layer_icons_changed(self, value):
        # value is a CallbackDict, cast to dict
        self.layer_icons = dict(value)
        self.set_viewer_id()
