from contextlib import contextmanager
from traitlets import Bool, Dict, Unicode, Integer, List, observe

from jdaviz.core.template_mixin import (TemplateMixin, LayerSelectMixin, DatasetSelectMixin)
from jdaviz.core.user_api import UserApiWrapper
from jdaviz.core.events import IconsUpdatedMessage, AddDataMessage
from jdaviz.utils import cmap_samples, is_not_wcs_only

__all__ = ['DataMenu']


SUBSET_TOOL_IDS = {'circle': 'bqplot:truecircle',
                   'rectangle': 'bqplot:rectangle',
                   'ellipse': 'bqplot:ellipse',
                   'annulus': 'bqplot:circannulus',
                   'xrange': 'bqplot:xrange',
                   'yrange': 'bqplot:yrange'}

SUBSET_NAMES = {v: k for k, v in SUBSET_TOOL_IDS.items()}


class DataMenu(TemplateMixin, LayerSelectMixin, DatasetSelectMixin):
    """Viewer Data Menu

    Only the following attributes and methods are available through the
    :ref:`public API <plugin-apis>`:

    * ``layer`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
        actively selected layer(s)
    * :meth:`set_layer_visibility`
    * :meth:`toggle_layer_visibility`
    * :meth:`create_subset`
    * :meth:`add_data`
    * :meth:`view_info`
    """
    template_file = __file__, "data_menu.vue"

    viewer_id = Unicode().tag(sync=True)
    viewer_reference = Unicode().tag(sync=True)

    layer_icons = Dict().tag(sync=True)  # read-only, see app.state.layer_icons
    viewer_icons = Dict().tag(sync=True)  # read-only, see app.state.viewer_icons

    visible_layers = Dict().tag(sync=True)  # read-only, set by viewer

    cmap_samples = Dict(cmap_samples).tag(sync=True)
    subset_tools = List().tag(sync=True)

    dm_layer_selected = List().tag(sync=True)

    selected_n_layers = Integer(0).tag(sync=True)
    selected_n_data = Integer(0).tag(sync=True)
    selected_n_subsets = Integer(0).tag(sync=True)

    info_enabled = Bool(False).tag(sync=True)
    info_tooltip = Unicode().tag(sync=True)

    delete_enabled = Bool(False).tag(sync=True)
    delete_tooltip = Unicode().tag(sync=True)

    subset_edit_enabled = Bool(False).tag(sync=True)
    subset_edit_tooltip = Unicode().tag(sync=True)

    dev_data_menu = Bool(False).tag(sync=True)

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer = viewer
        self._during_select_sync = False

        # TODO: refactor how this is applied by default to go through filters directly
        self.layer.remove_filter('filter_is_root')
        self.layer.add_filter(is_not_wcs_only)
        self.layer.multiselect = True
        self.layer._default_mode = 'empty'

        # we'll use a modified version of the dataset mixin to have a filtered
        # list of data entries in the app that are not in the current viewer.
        # changing the selection has no consequence.
        def data_not_in_viewer(data):
            return data.label not in self.layer.choices
        self.dataset.filters = ['is_not_wcs_only', 'not_child_layer', data_not_in_viewer]

        # first attach callback to catch any updates to viewer/layer icons and then
        # set their initial state
        self.hub.subscribe(self, IconsUpdatedMessage, self._on_app_icons_updated)
        self.hub.subscribe(self, AddDataMessage, handler=lambda _: self._set_viewer_id())
        self.viewer_icons = dict(self.app.state.viewer_icons)
        self.layer_icons = dict(self.app.state.layer_icons)

        # this currently assumes that toolbar.tools_data is set at init and does not change
        # if we ever support dynamic tool registration, this will need to be updated
        self.subset_tools = [{'id': k, 'img': v['img'], 'name': SUBSET_NAMES.get(k, k)}
                             for k, v in self._viewer.toolbar.tools_data.items()
                             if k in SUBSET_TOOL_IDS.values()]

    @property
    def user_api(self):
        expose = ['layer', 'set_layer_visibility', 'toggle_layer_visibility',
                  'create_subset', 'add_data', 'view_info']
        return UserApiWrapper(self, expose=expose)

    @observe('layer_items')
    def _update_data_not_in_viewer(self, msg):
        # changing the layers in the viewer needs to trigger an update to dataset_items
        # through the set filters
        self.dataset._on_data_changed()

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
        except Exception:  # pragma: no cover
            self._during_select_sync = False
            raise
        self._during_select_sync = False

    @observe('dm_layer_selected')
    def _dm_layer_selected_changed(self, event={}):
        if not hasattr(self, 'layer') or not self.layer.multiselect:  # pragma: no cover
            return
        if self._during_select_sync:
            return
        if len(event.get('new')) == len(event.get('old')):
            # not possible from UI interaction, but instead caused by a selected
            # layer being removed (deleting a selected subset, etc).  We want
            # to update dm_layer_selected in order to preserve layer.selected
            self._update_dm_layer_selected(event)
            return
        with self.during_select_sync():
            # map index in dm_layer_selected (inverse order of layer_items)
            # to set self.layer.selected
            length = len(self.layer_items)
            self.layer.selected = [self.layer_items[length-1-i]['label']
                                   for i in self.dm_layer_selected]

    @observe('layer_selected', 'layer_items')
    def _update_dm_layer_selected(self, event={}):
        if not hasattr(self, 'layer') or not self.layer.multiselect:  # pragma: no cover
            return
        if not self._during_select_sync:
            with self.during_select_sync():
                # map list of strings in self.layer.selected to indices in dm_layer_selected
                layer_labels = [layer['label'] for layer in self.layer_items][::-1]
                self.dm_layer_selected = [layer_labels.index(label) for label in self.layer.selected
                                          if label in layer_labels]

        # update internal counts and tooltips
        self.selected_n_layers = len(self.layer.selected)
        self.selected_n_subsets = len([l for l in self.layer.selected if l.startswith('Subset')])
        self.selected_n_data = self.selected_n_layers - self.selected_n_subsets

        # user-friendly representation of selection
        selected_repr = ""
        if self.selected_n_data:
            selected_repr += f"data ({self.selected_n_data})"
        if self.selected_n_subsets:
            if self.selected_n_data:
                selected_repr += " and"
            if self.selected_n_subsets == 1:
                selected_repr += f" subset ({self.selected_n_subsets})"
            else:
                selected_repr += f" subsets ({self.selected_n_subsets})"

        # layer info rules
        if self.selected_n_layers == 1 and not self.layer_items[self.dm_layer_selected[0]].get('from_plugin', False):
            self.info_enabled = True
            if self.selected_n_data == 1:
                self.info_tooltip = 'View metadata for selected data'
            else:
                self.info_tooltip = 'View subset info for selected subset'
        else:
            self.info_enabled = False
            if self.selected_n_layers == 0:
                self.info_tooltip = 'Select a layer to view info'
            else:
                self.info_tooltip = 'Select a single layer to view info'

        # delete layer rules
        if self.selected_n_layers == 0:
            self.delete_tooltip = "Select layer(s) to delete"
            self.delete_enabled = False
        else:
            self.delete_tooltip = f"Remove selected {selected_repr}"
            self.delete_enabled = True

        # subset edit rules
        if self.selected_n_subsets == 1:
            self.subset_edit_enabled = True
            self.subset_edit_tooltip = "Edit selected subset (COMING SOON)"
        else:
            self.subset_edit_enabled = False
            if self.selected_n_subsets == 0:
                self.subset_edit_tooltip = "Select a subset to edit"
            else:
                self.subset_edit_tooltip = "Select a single subset to edit"

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
            elif hasattr(layer.layer, 'data') and layer.layer.data.label == layer_label:
                layer.visible = layer.layer.label in self.visible_layers
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
        return self.set_layer_visibility(info.get('layer'), info.get('value'))  # pragma: no cover

    def add_data(self, data_label):
        """
        Add a dataset to the viewer.

        Parameters
        ----------
        data_label : str
            The label of the dataset to add to the viewer.
        """
        if data_label not in self.dataset.choices:
            raise ValueError(f"Data label '{data_label}' not able to be loaded into '{self.viewer_id}'.  Must be one of: {self.dataset.choices}")  # noqa
        return self.app.add_data_to_viewer(self.viewer_id, data_label)

    def vue_add_data_to_viewer(self, info, *args):
        self.add_data(info.get('data_label'))  # pragma: no cover

    def create_subset(self, subset_type):
        """
        Create a new subset in the viewer.  This sets the app-wide subset selection to 'Create New'
        and selects the appropriate tool in this viewer's toolbar.

        Parameters
        ----------
        subset_type : str
            The type of subset to create.  Must be one of 'circle', 'rectangle', 'ellipse',
            'annulus', 'xrange', or 'yrange'.
        """
        # clear previous selection, finalize subsets, temporarily sets default tool
        self._viewer.toolbar.active_tool_id = None
        # set toolbar to the selection, will also set app-wide subset selection to "Create New"
        # NOTE: supports passing either the user-friendly name or the actual ID
        self._viewer.toolbar.select_tool(SUBSET_TOOL_IDS.get(subset_type, subset_type))

    def vue_create_subset(self, info, *args):
        self.create_subset(info.get('subset_type'))  # pragma: no cover

    def view_info(self):
        """
        View info for the selected layer by opening either the metadata or subset plugin to the
        selected entry.
        """
        if len(self.layer.selected) != 1:
            raise ValueError("Only one layer can be selected to view info.")
        if self.layer.selected[0].startswith('Subset'):
            sp = self._viewer.jdaviz_helper.plugins.get('Subset Tools', None)
            if sp is None:
                return
            try:
                sp._obj.subset_select.selected = self.layer.selected[0]
            except ValueError:
                return
            sp.open_in_tray()
        else:
            mp = self._viewer.jdaviz_helper.plugins.get('Metadata', None)
            if mp is None:
                return
            try:
                mp.dataset.selected = self.layer.selected[0]
            except ValueError:
                return
            mp.open_in_tray()

    def vue_view_info(self, *args):
        self.view_info()  # pragma: no cover
