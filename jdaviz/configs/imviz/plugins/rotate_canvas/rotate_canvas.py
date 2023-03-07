from traitlets import Bool, observe

from jdaviz.configs.imviz.wcs_utils import get_compass_info
from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, CanvasRotationChangedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['RotateCanvas']


@tray_registry('imviz-rotate-canvas', label="Canvas Rotation", viewer_requirements='image')
class RotateCanvas(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Canvas Rotation Plugin Documentation <rotate-canvas>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
      Viewer to show orientation/compass information.
    * ``angle``:
      Angle to rotate the axes canvas, clockwise.
    * ``flip_horizontal``:
      Whether to flip the canvas horizontally, after applying rotation.
    * :meth:`set_north_up_east_left`
    * :meth:`set_north_up_east_right`
    """
    template_file = __file__, "rotate_canvas.vue"

    angle = FloatHandleEmpty(0).tag(sync=True)  # degrees, clockwise
    flip_horizontal = Bool(False).tag(sync=True)  # horizontal flip applied after rotation
    has_wcs = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('viewer', 'angle', 'flip_horizontal',
                                           'set_north_up_east_right', 'set_north_up_east_left'))

    @property
    def ref_data(self):
        return self.app.get_viewer_by_id(self.viewer.selected_id).state.reference_data

    def _on_viewer_data_changed(self, msg=None):
        if not self.viewer_selected:  # pragma: no cover
            return
        self.has_wcs = getattr(self.ref_data, 'coords', None) is not None

    @observe('viewer_selected')
    def _viewer_selected_changed(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            return
        self.angle = self.app._viewer_item_by_id(self.viewer.selected_id).get('rotation', 0)

    def _get_wcs_angles(self):
        if not self.has_wcs:
            raise ValueError("reference data does not have WCS, cannot determine orientation")
        ref_data = self.ref_data
        if ref_data is None:  # pragma: no cover
            raise ValueError("no data loaded in viewer, cannot determine orientation")
        _, _, _, _, _, _, degn, dege, flip = get_compass_info(ref_data.coords, ref_data.shape)
        return degn, dege, flip

    def set_north_up_east_left(self):
        degn, dege, flip = self._get_wcs_angles()
        self.angle = -degn
        self.flip_horizontal = flip

    def set_north_up_east_right(self):
        degn, dege, flip = self._get_wcs_angles()
        self.angle = -degn
        self.flip_horizontal = not flip

    def vue_set_north_up_east_left(self, *args, **kwargs):
        self.set_north_up_east_left()  # pragma: no cover

    def vue_set_north_up_east_right(self, *args, **kwargs):
        self.set_north_up_east_right()  # pragma: no cover

    @observe('angle')
    def _angle_changed(self, *args, **kwargs):
        try:
            angle = float(self.angle)
        except ValueError:  # pragma: no cover
            # empty string, etc
            angle = 0

        # Rotate selected viewer canvas. This changes zoom too.
        self.app._viewer_item_by_id(self.viewer.selected_id)['canvas_angle'] = angle
        # broadcast message (used by compass, etc)
        self.hub.broadcast(CanvasRotationChangedMessage(self.viewer.selected_id,
                                                        angle, self.flip_horizontal, sender=self))

    @observe('flip_horizontal')
    def _flip_changed(self, *args, **kwargs):
        self.app._viewer_item_by_id(self.viewer.selected_id)['canvas_flip_horizontal'] = self.flip_horizontal  # noqa
        self.hub.broadcast(CanvasRotationChangedMessage(self.viewer.selected_id,
                                                        self.angle, self.flip_horizontal,
                                                        sender=self))
