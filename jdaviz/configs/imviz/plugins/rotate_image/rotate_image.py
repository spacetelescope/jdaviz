from matplotlib.transforms import Affine2D
from traitlets import Any

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin


@tray_registry('imviz-rotate-image', label="Simple Image Rotation")
class RotateImageSimple(TemplateMixin, ViewerSelectMixin):
    template_file = __file__, "rotate_image.vue"

    angle = Any(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theta = 0  # degrees, counter-clockwise

    def vue_rotate_image(self, *args, **kwargs):
        # We only grab the value here to avoid constantly updating as
        # user is still entering or updating the value.
        try:
            self._theta = float(self.angle)
        except Exception:
            return

        viewer = self.app._viewer_by_id(self.viewer_selected)

        # Rotate selected viewer canvas.
        # TODO: This changes zoom too? astrofrog will fix translation issue?
        y_hub = (viewer.scales['y'].min + viewers.scales['y'].max) / 2
        x_hub = (viewer.scales['x'].min + viewer.scales['x'].max) / 2
        affine_transform = Affine2D().rotate_deg_around(y_hub, x_hub, self._theta)
        viewer.state.affine_matrix = affine_transform

        # TODO: Does the zoom box behave? If not, we need to disable it.
        # Update Compass plugin.
        viewer.on_limits_change()
