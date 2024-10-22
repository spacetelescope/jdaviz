from traitlets import Dict, Unicode

from jdaviz.core.template_mixin import TemplateMixin, LayerSelectMixin
from jdaviz.core.user_api import UserApiWrapper
from jdaviz.core.events import IconsUpdatedMessage, AddDataMessage
from jdaviz.utils import cmap_samples, is_not_wcs_only

__all__ = ['DataMenu']


class DataMenu(TemplateMixin, LayerSelectMixin):
    """Viewer Data Menu

    Only the following attributes and methods are available through the
    :ref:`public API <plugin-apis>`:

    * ``layer`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
    """
    template_file = __file__, "data_menu.vue"

    viewer_id = Unicode().tag(sync=True)
    viewer_reference = Unicode().tag(sync=True)

    layer_icons = Dict().tag(sync=True)  # read-only, see app.state.layer_icons
    viewer_icons = Dict().tag(sync=True)  # read-only, see app.state.viewer_icons

    visible_layers = Dict().tag(sync=True)  # read-only, set by viewer

    cmap_samples = Dict(cmap_samples).tag(sync=True)

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer = viewer

        # TODO: refactor how this is applied by default to go through filters directly
        self.layer.remove_filter('filter_is_root')
        self.layer.add_filter(is_not_wcs_only)

        # first attach callback to catch any updates to viewer/layer icons and then
        # set their initial state
        self.hub.subscribe(self, IconsUpdatedMessage, self._on_app_icons_updated)
        self.hub.subscribe(self, AddDataMessage, handler=lambda _: self._set_viewer_id())
        self.viewer_icons = dict(self.app.state.viewer_icons)
        self.layer_icons = dict(self.app.state.layer_icons)

    @property
    def user_api(self):
        expose = ['layer', 'set_layer_visibility', 'toggle_layer_visibility']
        return UserApiWrapper(self, expose=expose)

    def _set_viewer_id(self):
        # viewer_ids are not populated on the viewer at init, so we'll keep checking and set
        # these the first time that they are available
        if len(self.viewer_id) and len(self.viewer_reference):
            return
        try:
            self.viewer_id = getattr(self._viewer, '_reference_id', '')
            self.viewer_reference = self._viewer.reference
            self.layer.viewer = self._viewer.reference
        except AttributeError:
            return

    def _on_app_icons_updated(self, msg):
        if msg.icon_type == 'viewer':
            self.viewer_icons = msg.icons
        elif msg.icon_type == 'layer':
            self.layer_icons = msg.icons
        self._set_viewer_id()

    def set_layer_visibility(self, layer_label, visible=True):
        """
        Set the visibility of a layer in the viewer.

        Parameters
        ----------
        layer_label : str
            The label of the layer to set the visibility of.
        visible : bool
            Whether the layer should be visible or not.

        Returns
        -------
        dict
            A dictionary of the current visible layers.
        """
        # TODO: may need to be generalized to also support subset layers
        self.app.set_data_visibility(self.viewer_id, layer_label, visible=visible)
        return self.visible_layers

    def toggle_layer_visibility(self, layer_label):
        """
        Toggle the visibility of a layer in the viewer.

        Parameters
        ----------
        layer_label : str
            The label of the layer to toggle the visibility of.

        Returns
        -------
        bool
            The new visibility state of the layer.
        """
        visible = not layer_label in self.visible_layers
        self.set_layer_visibility(layer_label, visible=visible)
        return visible

    def vue_set_layer_visibility(self, info, *args):
        return self.set_layer_visibility(info.get('layer'), info.get('value'))