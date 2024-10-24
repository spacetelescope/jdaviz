from contextlib import contextmanager
from traitlets import Bool, Dict, Unicode, List, observe

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
        actively selected layer(s)
    * :meth:`set_layer_visibility`
    * :meth:`toggle_layer_visibility`
    """
    template_file = __file__, "data_menu.vue"

    viewer_id = Unicode().tag(sync=True)
    viewer_reference = Unicode().tag(sync=True)

    layer_icons = Dict().tag(sync=True)  # read-only, see app.state.layer_icons
    viewer_icons = Dict().tag(sync=True)  # read-only, see app.state.viewer_icons

    visible_layers = Dict().tag(sync=True)  # read-only, set by viewer

    cmap_samples = Dict(cmap_samples).tag(sync=True)

    dm_layer_selected = List().tag(sync=True)

    dev_data_menu = Bool(False).tag(sync=True)

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer = viewer
        self._during_select_sync = False

        # TODO: refactor how this is applied by default to go through filters directly
        self.layer.remove_filter('filter_is_root')
        self.layer.add_filter(is_not_wcs_only)
        self.layer.multiselect = True

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

    @contextmanager
    def during_select_sync(self):
        self._during_select_sync = True
        try:
            yield
        except Exception:
            self._during_select_sync = False
            raise
        self._during_select_sync = False

    @observe('dm_layer_selected')
    def _dm_layer_selected_changed(self, *args):
        if not hasattr(self, 'layer') or not self.layer.multiselect:
            return
        if self._during_select_sync:
            return
        with self.during_select_sync():
            # map index in dm_layer_selected (inverse order of layer_items)
            # to set self.layer.selected
            self.layer.selected = [self.layer_items[-i]['label'] for i in self.dm_layer_selected]

    @observe('layer_selected', 'layer_items')
    def _update_dm_layer_selected(self, *args):
        if not hasattr(self, 'layer') or not self.layer.multiselect:
            return
        if self._during_select_sync:
            return
        with self.during_select_sync():
            # map list of strings in self.layer.selected to indices in dm_layer_selected
            layer_labels = [layer['label'] for layer in self.layer_items][::-1]
            self.dm_layer_selected = [layer_labels.index(label) for label in self.layer.selected]

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
        for layer in self._viewer.layers:
            if layer.layer.label == layer_label:
                layer.visible = visible
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
        visible = layer_label not in self.visible_layers
        self.set_layer_visibility(layer_label, visible=visible)
        return visible

    def vue_set_layer_visibility(self, info, *args):
        return self.set_layer_visibility(info.get('layer'), info.get('value'))
