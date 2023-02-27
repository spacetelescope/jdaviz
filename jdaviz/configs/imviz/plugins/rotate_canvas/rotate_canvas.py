from traitlets import observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import CanvasRotationChangedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi


@tray_registry('imviz-rotate-canvas', label="Canvas Rotation")
class RotateCanvasSimple(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "rotate_canvas.vue"

    angle = FloatHandleEmpty(0).tag(sync=True)  # degrees, clockwise

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theta = 0  # degrees, clockwise

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('viewer', 'angle'))

    @observe('angle')
    def _angle_changed(self, *args, **kwargs):
        try:
            angle = float(self.angle)
        except ValueError:
            # empty string, etc
            angle = 0

        # Rotate selected viewer canvas. This changes zoom too.
        self.app._viewer_item_by_id(self.viewer_selected)['rotation'] = angle
        # broadcast message (used by compass, etc)
        self.hub.broadcast(CanvasRotationChangedMessage(self.viewer_selected, angle, sender=self))
