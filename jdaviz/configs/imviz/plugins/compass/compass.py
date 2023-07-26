from traitlets import Bool, Float, Unicode, observe

from jdaviz.core.events import AddDataMessage, RemoveDataMessage, CanvasRotationChangedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Compass']


@tray_registry('imviz-compass', label="Compass")
class Compass(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Compass Plugin Documentation <imviz-compass>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
      Viewer to show orientation/compass information.
    * ``data_label``: label of the top-layer shown in the compass (read-only)
    """
    template_file = __file__, "compass.vue"
    uses_active_status = Bool(True).tag(sync=True)

    icon = Unicode("").tag(sync=True)
    data_label = Unicode("").tag(sync=True)
    img_data = Unicode("").tag(sync=True)
    canvas_angle = Float(0).tag(sync=True)  # set by canvas rotation plugin
    canvas_flip_horizontal = Bool(False).tag(sync=True)  # set by canvas rotation plugin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, CanvasRotationChangedMessage, handler=self._on_canvas_rotation_changed)  # noqa

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('viewer',), readonly=('data_label',))

    def _on_viewer_data_changed(self, msg=None):
        if self.viewer_selected:
            viewer = self.viewer.selected_obj
            viewer.on_limits_change()  # Force redraw

    def _on_canvas_rotation_changed(self, msg=None):
        viewer_id = msg.viewer_id
        if viewer_id != self.viewer_selected:
            return

        self._set_compass_rotation()

    def _set_compass_rotation(self):
        viewer_item = self.app._viewer_item_by_id(self.viewer.selected_id)
        self.canvas_angle = viewer_item.get('canvas_angle', 0)  # noqa
        self.canvas_flip_horizontal = viewer_item.get('canvas_flip_horizontal', False)

    @observe("viewer_selected", "is_active")
    def _compass_with_new_viewer(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            # mixin object not yet initialized
            return

        # There can be only one!
        for vid, viewer in self.app._viewer_store.items():
            if vid == self.viewer.selected_id and self.plugin_opened:
                viewer.compass = self
                viewer.on_limits_change()  # Force redraw

                self._set_compass_rotation()
            else:
                viewer.compass = None

    def clear_compass(self):
        """Clear the content of the plugin."""
        self.icon = ''
        self.data_label = ''
        self.img_data = ''

    def draw_compass(self, data_label, img_data):
        """Draw compass in the plugin.
        Input is rendered buffer from Matplotlib.

        """
        if self.app.loading or (icn := self.app.state.layer_icons.get(data_label)) is None:
            return

        self.icon = icn
        self.data_label = data_label
        self.img_data = img_data
