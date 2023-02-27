from traitlets import Float, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi


@tray_registry('imviz-rotate-canvas', label="Canvas Rotation")
class RotateCanvasSimple(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "rotate_canvas.vue"

    angle = Float(0).tag(sync=True)  # degrees, clockwise

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theta = 0  # degrees, clockwise

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('viewer', 'angle'))

    @observe('angle')
    def _angle_changed(self, *args, **kwargs):
        # Rotate selected viewer canvas. This changes zoom too.
        self.app._viewer_item_by_id(self.viewer_selected)['rotation'] = float(self.angle)

        # Update Compass plugin.
        self.viewer.selected_obj.on_limits_change()
