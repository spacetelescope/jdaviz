from traitlets import Any

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin


@tray_registry('imviz-rotate-image', label="Simple Image Rotation")
class RotateImageSimple(TemplateMixin, ViewerSelectMixin):
    template_file = __file__, "rotate_image.vue"

    angle = Any(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theta = 0  # degrees, clockwise

    def vue_rotate_image(self, *args, **kwargs):
        # We only grab the value here to avoid constantly updating as
        # user is still entering or updating the value.
        try:
            self._theta = float(self.angle)
        except Exception:
            return

        viewer = self.app._viewer_by_id(self.viewer_selected)

        # Rotate selected viewer canvas. This changes zoom too.
        self.app._viewer_item_by_id(self.viewer_selected)['rotation'] = self._theta

        # Update Compass plugin.
        viewer.on_limits_change()
