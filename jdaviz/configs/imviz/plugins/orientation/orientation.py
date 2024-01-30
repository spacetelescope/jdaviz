from traitlets import List, Unicode, Bool, Dict, observe

from glue.core.message import (
    DataCollectionAddMessage, SubsetCreateMessage, SubsetDeleteMessage
)
from glue.core.subset import Subset
from glue.core.subset_group import GroupedSubset

import astropy.units as u
from jdaviz.configs.imviz.helper import link_image_data, base_wcs_layer_label
from jdaviz.configs.imviz.wcs_utils import (
    get_compass_info, _get_rotated_nddata_from_label
)
from jdaviz.core.events import (
    LinkUpdatedMessage, ExitBatchLoadMessage, ChangeRefDataMessage,
    AstrowidgetMarkersChangedMessage, MarkersPluginUpdate,
    SnackbarMessage, ViewerAddedMessage, AddDataMessage
)
from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin, SelectPluginComponent, LayerSelect, ViewerSelectMixin, AutoTextField
)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Orientation']

link_type_msg_to_trait = {'pixels': 'Pixels', 'wcs': 'WCS'}


@tray_registry('imviz-orientation', label="Orientation", viewer_requirements="image")
class Orientation(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Orientation Plugin Documentation <imviz-orientation>` for more details.

    .. note::
       Changing linking after adding markers via
       `~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers` is unsupported and
       will raise an error requiring resetting the markers manually via
       `~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers`
       or clicking a button in the plugin first.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``link_type`` (`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``wcs_use_affine``
    * ``delete_subsets``
    * ``viewer``
    * ``orientation``
    * ``rotation_angle``
    * ``east_left``
    * ``add_orientation``
    """
    template_file = __file__, "orientation.vue"

    link_type_items = List().tag(sync=True)
    link_type_selected = Unicode().tag(sync=True)
    wcs_use_fallback = Bool(True).tag(sync=True)
    wcs_use_affine = Bool(True).tag(sync=True)
    wcs_linking_available = Bool(False).tag(sync=True)

    need_clear_astrowidget_markers = Bool(False).tag(sync=True)
    plugin_markers_exist = Bool(False).tag(sync=True)
    linking_in_progress = Bool(False).tag(sync=True)
    need_clear_subsets = Bool(False).tag(sync=True)

    # rotation angle, counterclockwise [degrees]
    rotation_angle = FloatHandleEmpty(0).tag(sync=True)
    east_left = Bool(True).tag(sync=True)  # set convention for east left of north

    icons = Dict().tag(sync=True)

    viewer_items = List().tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)
    orientation_layer_items = List().tag(sync=True)
    orientation_layer_selected = Unicode().tag(sync=True)

    new_layer_label = Unicode().tag(sync=True)
    new_layer_label_default = Unicode().tag(sync=True)
    new_layer_label_auto = Bool(True).tag(sync=True)

    multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.icons = {k: v for k, v in self.app.state.icons.items()}

        self.link_type = SelectPluginComponent(self,
                                               items='link_type_items',
                                               selected='link_type_selected',
                                               manual_options=['Pixels', 'WCS'])

        self.orientation = LayerSelect(
            self, 'orientation_layer_items', 'orientation_layer_selected', 'viewer_selected',
            'multiselect', only_wcs_layers=True
        )
        self.orientation_layer_label = AutoTextField(
            self, 'new_layer_label', 'new_layer_label_default', 'new_layer_label_auto', None
        )

        self.hub.subscribe(self, LinkUpdatedMessage,
                           handler=self._on_link_updated)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_new_app_data)

        self.hub.subscribe(self, ExitBatchLoadMessage,
                           handler=self._on_new_app_data)

        self.hub.subscribe(self, AstrowidgetMarkersChangedMessage,
                           handler=self._on_astrowidget_markers_changed)

        self.hub.subscribe(self, MarkersPluginUpdate,
                           handler=self._on_markers_plugin_update)

        self.hub.subscribe(self, ChangeRefDataMessage,
                           handler=self._on_refdata_change)

        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=self._on_subset_change)

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_subset_change)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=self._on_viewer_added)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_data_add_to_viewer)

        self._update_layer_label_default()

    @property
    def user_api(self):
        return PluginUserApi(
            self,
            expose=(
                'link_type', 'wcs_use_affine', 'delete_subsets',
                'viewer', 'orientation',
                'rotation_angle', 'east_left', 'add_orientation'
            )
        )

    def _on_link_updated(self, msg):
        self.link_type.selected = link_type_msg_to_trait[msg.link_type]
        self.linking_in_progress = True
        self.wcs_use_fallback = msg.wcs_use_fallback
        self.wcs_use_affine = msg.wcs_use_affine

    def _link_image_data(self):
        link_image_data(
            self.app,
            link_type=self.link_type.selected.lower(),
            wcs_fallback_scheme='pixels' if self.wcs_use_fallback else None,
            wcs_use_affine=self.wcs_use_affine,
            error_on_fail=False,
            update_plugin=False)

    def _check_if_data_with_wcs_exists(self):
        for data in self.app.data_collection:
            if hasattr(data.coords, 'pixel_to_world'):
                self.wcs_linking_available = True
                return
        self.wcs_linking_available = False

    def _on_new_app_data(self, msg):
        if self.app._jdaviz_helper._in_batch_load > 0:
            return
        if isinstance(msg, DataCollectionAddMessage):
            components = [str(comp) for comp in msg.data.main_components]
            if "ra" in components or "Lon" in components:
                # linking currently removes any markers, so we want to skip
                # linking immediately after new markers are added.
                # Eventually we'll probably want to support linking WITH markers,
                # at which point this if-statement should be removed.
                return
        self._link_image_data()
        self._check_if_data_with_wcs_exists()

    def _on_astrowidget_markers_changed(self, msg):
        self.need_clear_astrowidget_markers = msg.has_markers

    def _on_markers_plugin_update(self, msg):
        self.plugin_markers_exist = msg.table_length > 0

    @observe('link_type_selected', 'wcs_use_fallback', 'wcs_use_affine')
    def _update_link(self, msg={}):
        """Run link_image_data with the selected parameters."""
        if not hasattr(self, 'link_type'):
            # could happen before plugin is fully initialized
            return

        if msg.get('name', None) == 'wcs_use_affine' and self.link_type.selected == 'Pixels':
            # approximation doesn't apply, avoid updating when not necessary!
            return

        if self.linking_in_progress:
            return

        if self.need_clear_subsets:
            raise ValueError("Link type can only be changed after existing subsets "
                             f"are deleted, but {len(self.app.data_collection.subset_groups)} "
                             f"subset(s) still exist. To delete them, you can use "
                             f"`delete_subsets()` from the plugin API.")

        self.linking_in_progress = True

        if self.need_clear_astrowidget_markers:
            setattr(self, msg.get('name'), msg.get('old'))
            self.linking_in_progress = False
            raise ValueError(f"cannot change linking with markers present (value reverted to "
                             f"'{msg.get('old')}'), call viewer.reset_markers()")

        if self.link_type.selected == 'Pixels':
            self.wcs_use_affine = True

        self._link_image_data()

        # load data into the viewer that are now compatible with the
        # new link type, remove data from the viewer that are now
        # incompatible:
        wcs_linked = self.link_type.selected == 'WCS'
        viewer_selected = self.app.get_viewer(self.viewer.selected)

        data_in_viewer = self.app.get_viewer(viewer_selected.reference).data()

        for data in self.app.data_collection:
            is_wcs_only = data.meta.get(self.app._wcs_only_label, False)
            has_wcs = hasattr(data.coords, 'pixel_to_world')
            if not is_wcs_only:
                if data in data_in_viewer and wcs_linked and not has_wcs:
                    # data is in viewer but must be removed:
                    self.app.remove_data_from_viewer(viewer_selected.reference, data.label)
                    self.hub.broadcast(SnackbarMessage(
                        f"Data '{data.label}' does not have a valid WCS - removing from viewer.",
                        sender=self, color="warning"))

        if wcs_linked:
            self._send_wcs_layers_to_all_viewers()

        self.linking_in_progress = False
        self._update_layer_label_default()

        # Clear previous zoom limits because they no longer mean anything.
        for v in self.app._viewer_store.values():
            v._prev_limits = None

    def _on_subset_change(self, msg):
        self.need_clear_subsets = len(self.app.data_collection.subset_groups) > 0

    def delete_subsets(self):
        # subsets will be deleted on changing link type:
        for subset_group in self.app.data_collection.subset_groups:
            self.app.data_collection.remove_subset_group(subset_group)

    def vue_delete_subsets(self, *args):
        self.delete_subsets()

    def vue_reset_astrowidget_markers(self, *args):
        for viewer in self.app._viewer_store.values():
            viewer.reset_markers()

    def _get_wcs_angles(self, first_loaded_image=None):
        if first_loaded_image is None:
            first_loaded_image = self.viewer.selected_obj.first_loaded_data
        degn, dege, flip = get_compass_info(
            first_loaded_image.coords, first_loaded_image.shape
        )[-3:]
        return degn, dege, flip

    def rotation_angle_deg(self, rotation_angle=None):
        if rotation_angle is None:
            rotation_angle = self.rotation_angle

        if rotation_angle is not None:
            if (
                (isinstance(rotation_angle, str) and len(rotation_angle)) or
                isinstance(rotation_angle, (int, float))
            ):
                return float(rotation_angle) * u.deg
        return 0 * u.deg

    def add_orientation(self, rotation_angle=None, east_left=None, label=None,
                        set_on_create=True, wrt_data=None):
        """
        Add new orientation options.

        Parameters
        ----------
        rotation_angle : float, optional
            Desired sky orientation angle in degrees.
            If `None`, the value will follow ``self.rotation_angle``.
            If nothing is set anywhere, it defaults to zero degrees.

        east_left : bool, optional
            Set to `True` if you want N-up E-left or `False` for N-up E-right.
            If `None`, the value will follow ``self.east_left``.

        label : str, optional
            Data label for this new orientation layer.
            If `None`, the value will follow ``self.new_layer_label``.

        set_on_create : bool, optional
            If `True`, this new orientation layer will become active
            on creation. Otherwise, it will be created but stay inactive
            in the background.

        wrt_data : str, optional
            Orientation calculations is done with respect to this data WCS.
            If `None`, it grabs the first loaded data in the selected viewer
            (may or may not be visible); If no data is loaded in the viewer,
            nothing will be done.

        """
        if self.link_type_selected != 'WCS':
            raise ValueError("must be aligned by WCS to add orientation options")

        if wrt_data is None:
            # if not specified, use first-loaded image layer as the
            # default rotation:
            wrt_data = self.viewer.selected_obj.first_loaded_data
            if wrt_data is None:  # Nothing in viewer
                return

        rotation_angle = self.rotation_angle_deg(rotation_angle)
        if east_left is None:
            east_left = self.east_left
        if label is None:
            label = self.new_layer_label

        # Default rotation is the same orientation as the original reference data:
        degn = self._get_wcs_angles(first_loaded_image=wrt_data)[0]

        if east_left:
            rotation_angle = -degn * u.deg + rotation_angle
        else:
            rotation_angle = (180 - degn) * u.deg - rotation_angle

        ndd = _get_rotated_nddata_from_label(
            app=self.app,
            data_label=wrt_data.label,
            rotation_angle=rotation_angle,
            target_wcs_east_left=east_left,
            target_wcs_north_up=True,
        )

        self.app._jdaviz_helper.load_data(
            ndd, data_label=label
        )

        # add orientation layer to all viewers:
        for viewer_ref in self.app._viewer_store:
            self._add_data_to_viewer(label, viewer_ref)

        if set_on_create:
            self.orientation.selected = label

    def _add_data_to_viewer(self, data_label, viewer_id):
        viewer = self.app.get_viewer_by_id(viewer_id)

        wcs_only_layers = viewer.state.wcs_only_layers
        if data_label not in wcs_only_layers:
            self.app.add_data_to_viewer(viewer_id, data_label)

    def _on_viewer_added(self, msg):
        self._send_wcs_layers_to_all_viewers(viewers_to_update=[msg._viewer_id])

    @observe('viewer_items')
    def _send_wcs_layers_to_all_viewers(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            return

        wcs_only_layers = self.app._jdaviz_helper.default_viewer._obj.state.wcs_only_layers

        viewers_to_update = kwargs.get(
            'viewers_to_update', self.app._viewer_store.keys()
        )
        for viewer_ref in viewers_to_update:
            self.viewer.selected = viewer_ref
            self.orientation.update_wcs_only_filter(wcs_only=self.link_type_selected == 'WCS')
            for wcs_layer in wcs_only_layers:
                if wcs_layer not in self.viewer.selected_obj.layers:
                    self.app.add_data_to_viewer(viewer_ref, wcs_layer)
            if (
                self.orientation.selected not in
                    self.viewer.selected_obj.state.wcs_only_layers and
                    self.link_type_selected == 'WCS'
            ):
                self.orientation.selected = base_wcs_layer_label

    def _on_data_add_to_viewer(self, msg):
        all_wcs_only_layers = all(
            layer.layer.meta.get(self.app._wcs_only_label)
            for layer in self.viewer.selected_obj.layers
            if hasattr(layer.layer, "meta")
        )
        if all_wcs_only_layers and msg.data.meta.get(self.app._wcs_only_label, False):
            # on adding first data layer, reset the limits:
            self.viewer.selected_obj.state.reset_limits()

    def vue_add_orientation(self, *args, **kwargs):
        self.add_orientation(set_on_create=True)

    @observe('orientation_layer_selected')
    def _change_reference_data(self, *args, **kwargs):
        if self._refdata_change_available:
            self.app._change_reference_data(
                self.orientation.selected, viewer_id=self.viewer.selected
            )
            viewer_item = self.app._viewer_item_by_id(self.viewer.selected)
            if viewer_item != self.orientation.selected:
                viewer_item['reference_data_label'] = self.orientation.selected

    def _on_refdata_change(self, msg):

        if hasattr(self, 'viewer'):
            ref_data = self.ref_data
            viewer = self.viewer.selected_obj

            # don't select until reference data are available:
            if ref_data is not None:
                link_type = viewer.get_link_type(ref_data.label)
                if link_type != 'self':
                    self.link_type_selected = link_type_msg_to_trait[link_type]
            elif not len(viewer.data()):
                self.link_type_selected = link_type_msg_to_trait['pixels']

            if msg.data.label not in self.orientation.choices:
                return

            self.orientation.selected = msg.data.label

            # we never want to highlight subsets of pixels within WCS-only layers,
            # so if this layer is an ImageSubsetLayerState on a WCS-only layer,
            # ensure that it is never visible:
            for layer in viewer.state.layers:
                if (
                    hasattr(layer.layer, 'label') and
                    layer.layer.label.startswith("Subset") and
                    layer.layer.data.meta.get("_WCS_ONLY", False)
                ):
                    layer.visible = False

    @property
    def ref_data(self):
        if hasattr(self, 'viewer'):
            return self.app.get_viewer_by_id(self.viewer.selected).state.reference_data
        return None

    @property
    def _refdata_change_available(self):
        viewer = self.app.get_viewer(self.viewer.selected)
        selected_layer = [lyr.layer for lyr in viewer.layers
                          if lyr.layer.label == self.orientation.selected]
        if len(selected_layer):
            is_subset = isinstance(selected_layer[0], (Subset, GroupedSubset))
        else:
            is_subset = False
        return (
            len(self.orientation.selected) and
            len(self.viewer.selected) and
            not is_subset
        )

    @observe('viewer_selected')
    def _on_viewer_change(self, msg={}):
        # don't update choices until viewer is available:
        ref_data = self.ref_data
        if hasattr(self, 'viewer') and ref_data is not None:
            if ref_data.label in self.orientation.choices:
                self.orientation.selected = ref_data.label

    def create_north_up_east_left(self, label="North-up, East-left", set_on_create=False):
        """
        Set the rotation angle and flip to achieve North up and East left
        according to the reference image WCS.
        """
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self.add_orientation(rotation_angle=degn, east_left=True,
                                 label=label, set_on_create=set_on_create)
        elif set_on_create:
            self.orientation.selected = label

    def create_north_up_east_right(self, label="North-up, East-right", set_on_create=False):
        """
        Set the rotation angle and flip to achieve North up and East right
        according to the reference image WCS.
        """
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self.add_orientation(rotation_angle=180 - degn, east_left=False,
                                 label=label, set_on_create=set_on_create)
        elif set_on_create:
            self.orientation.selected = label

    def vue_select_north_up_east_left(self, *args, **kwargs):
        self.create_north_up_east_left(set_on_create=True)

    def vue_select_north_up_east_right(self, *args, **kwargs):
        self.create_north_up_east_right(set_on_create=True)

    def vue_select_default_orientation(self, *args, **kwargs):
        self.orientation.selected = base_wcs_layer_label

    @observe('east_left', 'rotation_angle')
    def _update_layer_label_default(self, event={}):
        self.new_layer_label_default = (
            f'CCW {self.rotation_angle_deg():.2f} ' +
            ('(E-left)' if self.east_left else '(E-right)')
        )
