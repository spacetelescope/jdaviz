import os

from contextlib import contextmanager
from traitlets import Bool, Dict, Unicode, Integer, List, observe

from jdaviz.core.template_mixin import (TemplateMixin, LayerSelect,
                                        LayerSelectMixin, DatasetSelectMixin)
from jdaviz.core.user_api import UserApiWrapper
from jdaviz.core.events import (IconsUpdatedMessage, AddDataMessage,
                                ChangeRefDataMessage, ViewerRenamedMessage)
from jdaviz.utils import cmap_samples, is_not_wcs_only

from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode, NewMode)
from glue.icons import icon_path
from glue_jupyter.common.toolbar_vuetify import read_icon

__all__ = ['DataMenu']


SUBSET_TOOL_IDS = {'circle': 'bqplot:truecircle',
                   'rectangle': 'bqplot:rectangle',
                   'ellipse': 'bqplot:ellipse',
                   'annulus': 'bqplot:circannulus',
                   'xrange': 'bqplot:xrange',
                   'yrange': 'bqplot:yrange'}

SUBSET_NAMES = {v: k for k, v in SUBSET_TOOL_IDS.items()}

SUBSET_MODES = {
    'new': NewMode,
    'replace': ReplaceMode,
    'or': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'andnot': AndNotMode,
}


class DataMenu(TemplateMixin, LayerSelectMixin, DatasetSelectMixin):
    """Viewer Data Menu

    Only the following attributes and methods are available through the
    :ref:`public API <plugin-apis>`:

    * :meth:`open_menu`
    * :meth:`data_labels_loaded`
    * :meth:`data_labels_visible`
    * :meth:`data_labels_unloaded`
    * ``layer`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
        actively selected layer(s)
    * ``orientation`` (:class:`~jdaviz.core.template_mixin.LayerSelect`):
        orientation chosen for the viewer, if applicable
    * :meth:`set_layer_visibility`
    * :meth:`toggle_layer_visibility`
    * :meth:`create_subset`
    * :meth:`modify_subset`
    * :meth:`add_data`
    * :meth:`view_info`
    * :meth:`remove_from_viewer`
    * :meth:`remove_from_app`
    """
    template_file = __file__, "data_menu.vue"

    force_open_menu = Bool(False).tag(sync=True)

    viewer_id = Unicode().tag(sync=True)
    viewer_reference = Unicode().tag(sync=True)

    icons = Dict().tag(sync=True)
    layer_icons = Dict().tag(sync=True)  # read-only, see app.state.layer_icons
    viewer_icons = Dict().tag(sync=True)  # read-only, see app.state.viewer_icons

    visible_layers = Dict().tag(sync=True)  # read-only, set by viewer

    orientation_enabled = Bool(False).tag(sync=True)
    orientation_align_by_wcs = Bool(False).tag(sync=True)
    orientation_layer_items = List().tag(sync=True)
    orientation_layer_selected = Unicode().tag(sync=True)

    cmap_samples = Dict(cmap_samples).tag(sync=True)
    subset_tools = List().tag(sync=True)

    dm_layer_selected = List().tag(sync=True)

    loaded_n_data = Integer(0).tag(sync=True)
    selected_n_layers = Integer(0).tag(sync=True)
    selected_n_data = Integer(0).tag(sync=True)
    selected_n_subsets = Integer(0).tag(sync=True)

    info_enabled = Bool(False).tag(sync=True)
    info_tooltip = Unicode().tag(sync=True)

    delete_enabled = Bool(False).tag(sync=True)
    delete_tooltip = Unicode().tag(sync=True)
    delete_viewer_tooltip = Unicode().tag(sync=True)
    delete_app_enabled = Bool(False).tag(sync=True)
    delete_app_tooltip = Unicode().tag(sync=True)

    subset_edit_enabled = Bool(False).tag(sync=True)
    subset_edit_tooltip = Unicode().tag(sync=True)

    subset_edit_modes = List().tag(sync=True)

    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer = viewer
        self._during_select_sync = False

        # TODO: refactor how this is applied by default to go through filters directly
        self.layer.remove_filter('filter_is_root')
        self.layer.add_filter(is_not_wcs_only)
        self.layer.multiselect = True
        self.layer.sort_by = 'zorder'
        self.layer._default_mode = 'empty'

        # we'll use a modified version of the dataset mixin to have a filtered
        # list of data entries in the app that are not in the current viewer.
        # changing the selection has no consequence.
        def data_not_in_viewer(data):
            return data.label not in self.layer.choices
        self.dataset.filters = ['is_not_wcs_only', 'not_child_layer', data_not_in_viewer]

        self.orientation = LayerSelect(self,
                                       'orientation_layer_items',
                                       'orientation_layer_selected',
                                       'viewer_id',
                                       only_wcs_layers=True)
        self.orientation_enabled = self.config == 'imviz'

        # first attach callback to catch any updates to viewer/layer icons and then
        # set their initial state
        self.hub.subscribe(self, IconsUpdatedMessage, self._on_app_icons_updated)
        self.hub.subscribe(self, AddDataMessage, handler=lambda _: self._set_viewer_id())
        self.hub.subscribe(self, ChangeRefDataMessage, handler=self._on_refdata_change)
        self.hub.subscribe(self, ViewerRenamedMessage, handler=self._on_viewer_renamed_message)
        self.viewer_icons = dict(self.app.state.viewer_icons)
        self.layer_icons = dict(self.app.state.layer_icons)

        self.subset_edit_modes = [{'glue_name': 'replace', 'icon': read_icon(os.path.join(icon_path("glue_replace", icon_format="svg")), 'svg+xml')},  # noqa
                                  {'glue_name': 'or', 'icon': read_icon(os.path.join(icon_path("glue_or", icon_format="svg")), 'svg+xml')},  # noqa
                                  {'glue_name': 'and', 'icon': read_icon(os.path.join(icon_path("glue_and", icon_format="svg")), 'svg+xml')},  # noqa
                                  {'glue_name': 'xor', 'icon': read_icon(os.path.join(icon_path("glue_xor", icon_format="svg")), 'svg+xml')},  # noqa
                                  {'glue_name': 'andnot', 'icon': read_icon(os.path.join(icon_path("glue_andnot", icon_format="svg")), 'svg+xml')}]  # noqa

        # this currently assumes that toolbar.tools_data is set at init and does not change
        # if we ever support dynamic tool registration, this will need to be updated
        self.subset_tools = [{'id': k, 'img': v['img'], 'name': SUBSET_NAMES.get(k, k)}
                             for k, v in self._viewer.toolbar.tools_data.items()
                             if k in SUBSET_TOOL_IDS.values()]

        self.icons = {k: v for k, v in self.app.state.icons.items()}

    @property
    def user_api(self):
        expose = ['open_menu', 'layer', 'set_layer_visibility', 'toggle_layer_visibility',
                  'create_subset', 'modify_subset', 'add_data', 'view_info',
                  'remove_from_viewer', 'remove_from_app']
        readonly = ['data_labels_loaded', 'data_labels_visible', 'data_labels_unloaded']
        if self.app.config == 'imviz':
            expose += ['orientation']
        return UserApiWrapper(self, expose=expose, readonly=readonly)

    def open_menu(self):
        """
        Open all instances of the data menu.
        """
        self.force_open_menu = True

    @property
    def existing_subset_labels(self):
        return [sg.label for sg in self.app.data_collection.subset_groups]

    @property
    def data_labels_loaded(self):
        return [layer['label'] for layer in self.layer_items
                if layer['label'] not in self.existing_subset_labels]

    @property
    def data_labels_visible(self):
        return [layer['label'] for layer in self.layer_items
                if layer['label'] not in self.existing_subset_labels and layer['visible']]

    @property
    def data_labels_unloaded(self):
        return self.dataset.choices

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

    def _on_refdata_change(self, msg):
        if msg.viewer_id != self.viewer_id:
            return
        self.orientation_align_by_wcs = self._viewer.state.reference_data.meta.get('_WCS_ONLY', False)  # noqa
        if self.orientation_align_by_wcs:
            with self.during_select_sync():
                self.orientation.selected = str(self._viewer.state.reference_data.label)

    def _on_viewer_renamed_message(self, msg):
        if self.viewer_reference == msg.old_viewer_ref:
            self.viewer_reference = msg.new_viewer_ref
            self._set_viewer_id()

    @observe('orientation_layer_selected')
    def _orientation_layer_selected_changed(self, event={}):
        if not hasattr(self, 'orientation'):
            return
        if self._during_select_sync:
            return
        op = self._viewer.jdaviz_helper.plugins['Orientation']
        op._obj.set_orientation_for_viewer(event.get('new'), self.viewer_id)

    @contextmanager
    def during_select_sync(self):
        self._during_select_sync = True
        try:
            yield
        except Exception:  # pragma: no cover
            self._during_select_sync = False
            raise
        self._during_select_sync = False

    @observe('dm_layer_selected', 'layer_multiselect')
    def _dm_layer_selected_changed(self, event={}):
        if not hasattr(self, 'layer'):  # pragma: no cover
            return
        if self._during_select_sync:
            return
        if event.get('name') == 'layer_multiselect' and event.get('new'):
            return
        if not self.layer.multiselect and len(self.dm_layer_selected) > 1:
            # vue will still treat the element as a list, so we will include the
            # logic here to enforce single-select toggling
            self.dm_layer_selected = [self.dm_layer_selected[-1]]
            return
        if (event.get('name') == 'dm_layer_selected'
                and len(event.get('new')) == len(event.get('old'))):
            # not possible from UI interaction, but instead caused by a selected
            # layer being removed (deleting a selected subset, etc).  We want
            # to update dm_layer_selected in order to preserve layer.selected
            self._layers_changed(event)
            return
        with self.during_select_sync():
            # map index in dm_layer_selected (inverse order of layer_items)
            # to set self.layer.selected
            selected = [self.layer_items[i]['label']
                        for i in self.dm_layer_selected]
            if self.layer.multiselect:
                self.layer.selected = selected
            else:
                self.layer.selected = selected[0] if len(selected) else ''

    @observe('layer_selected', 'layer_items')
    def _layers_changed(self, event={}):
        if not hasattr(self, 'layer') or not self.layer.multiselect:  # pragma: no cover
            return
        if not self._during_select_sync:
            with self.during_select_sync():
                # map list of strings in self.layer.selected to indices in dm_layer_selected
                layer_labels = [layer['label'] for layer in self.layer_items]
                layer_selected = self.layer_selected if self.layer.multiselect else [self.layer_selected]  # noqa
                self.dm_layer_selected = [layer_labels.index(label) for label in layer_selected
                                          if label in layer_labels]

        subset_labels = self.existing_subset_labels

        if event.get('name') == 'layer_items':
            # changing the layers in the viewer needs to trigger an update to dataset_items
            # through the set filters
            self.dataset._update_items()
            self.loaded_n_data = len([lyr for lyr in self.layer.choices
                                      if lyr not in subset_labels])
            return

        # update internal counts and tooltips
        self.selected_n_layers = len(self.layer.selected)
        self.selected_n_subsets = len([lyr for lyr in self.layer.selected if lyr in subset_labels])
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
        if self.selected_n_layers == 1:
            if max(self.dm_layer_selected) >= len(self.layer_items):  # pragma: no cover
                # can happen during state transition but should immediately be followed up
                # with an update
                self.info_enabled = False
                self.info_tooltip = ''
            elif self.layer_items[self.dm_layer_selected[0]].get('from_plugin', False):
                self.info_enabled = False
                self.info_tooltip = 'Selected data layer is a plugin product and does not have metadata'  # noqa
            else:
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

        # delete from entire app rules
        subset_str = "subset" if self.selected_n_subsets == 1 else "subsets"
        if self.selected_n_subsets and self.selected_n_data:
            self.delete_viewer_tooltip = f"Remove selected data and hide selected {subset_str} in this viewer"  # noqa
        elif self.selected_n_data:
            self.delete_viewer_tooltip = "Remove selected data from this viewer"
        elif self.selected_n_subsets:
            self.delete_viewer_tooltip = f"Hide selected {subset_str} in this viewer"

        delete_app_tooltip = "Remove from all viewers and application (permanent, might affect existing subsets)"  # noqa
        if self.app.config == 'cubeviz':
            # forbid deleting non-plugin generated data
            selected_items = self.layer.selected_item
            for i, layer in enumerate(self.layer.selected):
                if (layer not in self.existing_subset_labels
                        and selected_items['from_plugin'][i] is None):
                    self.delete_app_enabled = False
                    self.delete_app_tooltip = f"Cannot delete imported data from {self.app.config}"
                    break
            else:
                self.delete_app_enabled = True
                self.delete_app_tooltip = delete_app_tooltip
        else:
            self.delete_app_enabled = True
            self.delete_app_tooltip = delete_app_tooltip

        # subset edit rules
        if self.selected_n_subsets == 1 and self.selected_n_layers == 1:
            self.subset_edit_enabled = True
            self.subset_edit_tooltip = f"Edit {self.layer_selected[0]}"
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
            if not visible and self.app._get_assoc_data_parent(layer.layer.label) == layer_label:
                # then this is a child-layer of a parent-layer that is being hidden
                # so also hide the child-layer
                layer.visible = False

        if visible and (parent_label := self.app._get_assoc_data_parent(layer_label)):
            # ensure the parent layer is also visible
            self.set_layer_visibility(parent_label, visible=True)

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

    def add_data(self, *data_labels):
        """
        Add a dataset to the viewer.

        Parameters
        ----------
        *data_labels : str
            The label(s) of the dataset to add to the viewer.
        """
        unavailable = [data_label for data_label in data_labels
                       if data_label not in self.dataset.choices]
        if len(unavailable):
            raise ValueError(f"Data labels {unavailable} not able to be loaded into '{self.viewer_id}'.  Must be one of: {self.dataset.choices}")  # noqa
        for data_label in data_labels:
            self.app.add_data_to_viewer(self.viewer_id, data_label)

    def vue_add_data_to_viewer(self, info, *args):
        self.add_data(info.get('data_label'))  # pragma: no cover

    def create_subset(self, subset_type):
        """
        Interactively create a new subset in the viewer.  This sets the app-wide subset
        selection to 'Create New' and selects the appropriate tool in this viewer's toolbar.

        Parameters
        ----------
        subset_type : str
            The type of subset to create.  Must be one of 'circle', 'rectangle', 'ellipse',
            'annulus', 'xrange', or 'yrange', and must be an available tool in this viewer.
        """
        # clear previous selection, finalize subsets, temporarily sets default tool
        self._viewer.toolbar.active_tool_id = None
        # set toolbar to the selection, will also set app-wide subset selection to "Create New"
        # NOTE: supports passing either the user-friendly name or the actual ID
        self._viewer.toolbar.select_tool(SUBSET_TOOL_IDS.get(subset_type, subset_type))

    def vue_create_subset(self, info, *args):
        self.create_subset(info.get('subset_type'))  # pragma: no cover

    def modify_subset(self, combination_mode, subset_type):
        """
        Interactively modify an existing subset in the viewer.  This sets the app-wide subset
        selection to the currently selected subset, mode to the selected combination_mode,
        and selects the appropriate tool in this viewer's toolbar.

        Parameters
        ----------
        combination_mode : str
            The combination mode to apply to the subset.  Must be one of 'replace', 'or', 'and',
            'xor', or 'andnot'.
        subset_type : str
            The type of subset to modify.  Must be one of 'circle', 'rectangle', 'ellipse',
            'annulus', 'xrange', or 'yrange', and must be an available tool in this viewer.
        """
        # future improvement: allow overriding layer.selected, with pre-validation
        if len(self.layer.selected) != 1:
            raise ValueError("Only one layer can be selected to modify subset.")
        if self.layer.selected[0] not in self.existing_subset_labels:
            raise ValueError("Selected layer is not a subset.")
        subset = self.layer.selected[0]

        # set tool first since that might default to "Create New"
        self._viewer.toolbar.select_tool(SUBSET_TOOL_IDS.get(subset_type, subset_type))
        # set subset selection to the subset to modify
        subset_grp = [sg for sg in self.app.data_collection.subset_groups if sg.label == subset]
        self.session.edit_subset_mode.edit_subset = subset_grp
        # set combination mode
        self.session.edit_subset_mode.mode = SUBSET_MODES.get(combination_mode)

    def vue_modify_subset(self, info, *args):
        self.modify_subset(info.get('combination_mode'),
                           info.get('subset_type'))  # pragma: no cover

    def view_info(self):
        """
        View info for the selected layer by opening either the metadata or subset plugin to the
        selected entry.
        """
        # future improvement: allow overriding layer.selected, with pre-validation
        if len(self.layer.selected) != 1:
            raise ValueError("Only one layer can be selected to view info.")
        if self.layer.selected[0] in self.existing_subset_labels:
            sp = self._viewer.jdaviz_helper.plugins.get('Subset Tools', None)
            if sp is None:  # pragma: no cover
                raise ValueError("subset tools plugin not available")
            sp._obj.subset.selected = self.layer.selected[0]
            sp.open_in_tray()
        else:
            mp = self._viewer.jdaviz_helper.plugins.get('Metadata', None)
            if mp is None:  # pragma: no cover
                raise ValueError("metadata plugin not available")
            mp.dataset.selected = self.layer.selected[0]
            mp.open_in_tray()

    def vue_view_info(self, *args):
        self.view_info()  # pragma: no cover

    def remove_from_viewer(self):
        """
        Remove the selected layers from the viewer.  For subset layers, this
        sets the visibility of the subset layer.  For data layers,
        this unloads the data from the viewer, but keeps it in the application or other viewers.
        """
        # future improvement: allow overriding layer.selected via *args, with pre-validation
        for layer in self.layer.selected:
            if layer in self.existing_subset_labels:
                self.set_layer_visibility(layer, visible=False)
            else:
                self.app.remove_data_from_viewer(self.viewer_id, layer)

    def vue_remove_from_viewer(self, *args):
        self.remove_from_viewer()  # pragma: no cover

    def remove_from_app(self):
        """
        Remove the selected layers from the entire app and all viewers.
        """
        # future improvement: allow overriding layer.selected via *args, with pre-validation
        for layer in self.layer.selected:
            if layer in self.existing_subset_labels:
                for sg in self.app.data_collection.subset_groups:
                    if sg.label == layer:
                        self.app.data_collection.remove_subset_group(sg)
                        break
            else:
                self.app.data_item_remove(layer)

    def vue_remove_from_app(self, *args):
        self.remove_from_app()  # pragma: no cover

    def vue_open_orientation_plugin(self, *args):
        op = self._viewer.jdaviz_helper.plugins.get('Orientation', None)
        if op is None:  # pragma: no cover
            raise ValueError("orientation plugin not available")
        op.open_in_tray()
