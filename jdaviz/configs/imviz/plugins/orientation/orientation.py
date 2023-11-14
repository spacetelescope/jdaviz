import os
from traitlets import List, Unicode, Bool, observe

from glue.core.message import (
    DataCollectionAddMessage, SubsetCreateMessage, SubsetDeleteMessage
)
from glue.core.subset import Subset
from glue.core.subset_group import GroupedSubset
from glue_jupyter.common.toolbar_vuetify import read_icon

import astropy.units as u
from jdaviz.configs.imviz.helper import (
    link_image_data, get_bottom_layer, base_wcs_layer_label
)
from jdaviz.configs.imviz.wcs_utils import (
    get_compass_info, _get_rotated_nddata_from_label
)
from jdaviz.core.events import (
    LinkUpdatedMessage, ExitBatchLoadMessage, ChangeRefDataMessage,
    AstrowidgetMarkersChangedMessage, MarkersPluginUpdate,
    SnackbarMessage
)
from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin, SelectPluginComponent, LayerSelect, ViewerSelectMixin, AutoTextField
)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR

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
    relink = Bool(True).tag(sync=True)
    east_left = Bool(True).tag(sync=True)  # set convention for east left of north

    icon_nuer = Unicode(
        read_icon(os.path.join(ICON_DIR, 'right-east.svg'), 'svg+xml')
    ).tag(sync=True)
    icon_nuel = Unicode(
        read_icon(os.path.join(ICON_DIR, 'left-east.svg'), 'svg+xml')
    ).tag(sync=True)

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

        self.link_type = SelectPluginComponent(self,
                                               items='link_type_items',
                                               selected='link_type_selected',
                                               manual_options=['WCS', 'Pixels'])

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
        self.orientation.only_wcs_layers = self.link_type_selected == 'WCS'
        self.orientation._on_layers_changed()

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
                # linking immediately after new markers are added
                # (see imviz.helper.link_image_data).
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
        """Run :func:`jdaviz.configs.imviz.helper.link_image_data`
        with the selected parameters.
        """
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
        wcs_linked = self.link_type.selected.lower() == 'wcs'
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

        self.linking_in_progress = False
        self._update_layer_label_default()

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

    def _get_wcs_angles(self):
        viewer = self.app.get_viewer(self.viewer.selected)
        first_loaded_image = get_bottom_layer(viewer)
        degn, dege, flip = get_compass_info(
            first_loaded_image.coords, first_loaded_image.shape
        )[-3:]
        return degn, dege, flip

    @property
    def rotation_angle_deg(self):
        if self.rotation_angle is not None:
            if (
                (isinstance(self.rotation_angle, str) and len(self.rotation_angle)) or
                isinstance(self.rotation_angle, (int, float))
            ):
                return float(self.rotation_angle) * u.deg
        return 0 * u.deg

    def add_orientation(self, data, set_on_create=True):
        # Default rotation is the same orientation as the original reference data:
        degn = self._get_wcs_angles()[0]

        if self.east_left:
            rotation_angle = -degn * u.deg + self.rotation_angle_deg
        else:
            rotation_angle = (180 - degn) * u.deg - self.rotation_angle_deg

        ndd = _get_rotated_nddata_from_label(
            app=self.app,
            data_label=data.label,
            rotation_angle=rotation_angle,
            target_wcs_east_left=self.east_left,
            target_wcs_north_up=True,
        )
        self._update_layer_label_default()

        # save the following data label since relinking will rename it:
        wcs_only_layer_label = self.orientation_layer_label.value

        self.app._jdaviz_helper.load_data(
            ndd, data_label=self.orientation_layer_label.value
        )
        if self.relink:
            # this will trigger linking by wcs if not already selected:
            self.link_type_selected = 'WCS'
            self._update_link()

        # changing link type has changed the traitlet, so we correct it:
        self.orientation_layer_label.value = wcs_only_layer_label

        # add orientation layer to all viewers:
        self._add_data_to_all_viewers(self.orientation_layer_label.value)

        if set_on_create:
            # set orientation (reference data layer) to be the new option:
            self.app._change_reference_data(
                self.orientation_layer_label.value, viewer_id=self.viewer.selected
            )

    def _add_data_to_all_viewers(self, data_label):
        for viewer_ref in self.viewer.choices:
            layers_in_viewer = [
                layer.layer.label for layer in
                self.app.get_viewer_by_id(self.viewer.selected).layers
            ]
            if data_label not in layers_in_viewer:
                self.app.add_data_to_viewer(viewer_ref, data_label, visible=False)

    def vue_add_orientation(self, *args, **kwargs):
        # TODO: move into add_orientation
        if 'reference_data' not in kwargs:
            # if not specified, use first-loaded image layer as the
            # default rotation:
            viewer = self.app.get_viewer(self.viewer.selected)
            reference_data = get_bottom_layer(viewer)
        self.add_orientation(reference_data, set_on_create=True)

    @observe('orientation_layer_selected')
    def _change_reference_data(self, *args, **kwargs):
        if self._refdata_change_available:
            self.app._change_reference_data(
                self.orientation.selected, viewer_id=self.viewer.selected
            )

    def _on_refdata_change(self, msg={}):
        self.orientation.only_wcs_layers = msg.data.meta.get('_WCS_ONLY', False)
        self.orientation._on_layers_changed()

        # don't select until viewer is available:
        if hasattr(self, 'viewer'):
            ref_data = self.ref_data
            viewer = self.app.get_viewer(self.viewer.selected)

            # don't select until reference data are available:
            if ref_data is not None:
                self.orientation.selected = ref_data.label
                link_type = viewer.get_link_type(ref_data.label)
                if link_type != 'self':
                    self.link_type_selected = link_type_msg_to_trait[link_type]
            elif not len(viewer.data()):
                self.link_type_selected = link_type_msg_to_trait['pixels']

        self._reset_default_rotation_options()

    def _reset_default_rotation_options(self):
        # return rotation options to these defaults:
        self.east_left = True
        self.rotation_angle = 0

    @property
    def ref_data(self):
        return self.app.get_viewer_by_id(self.viewer.selected).state.reference_data

    @property
    def _refdata_change_available(self):
        viewer = self.app.get_viewer(self.viewer.selected)
        ref_data = self.ref_data
        selected_layer = [lyr.layer for lyr in viewer.layers
                          if lyr.layer.label == self.orientation.selected]
        if len(selected_layer):
            is_subset = isinstance(selected_layer[0], (Subset, GroupedSubset))
        else:
            is_subset = False
        return (
            ref_data is not None and len(viewer.data()) and
            len(self.orientation.selected) and len(self.viewer.selected) and
            not is_subset
        )

    @observe('viewer_selected')
    def _on_viewer_change(self, msg={}):
        # don't update choices until viewer is available:
        if hasattr(self, 'viewer'):
            viewer = self.app.get_viewer(self.viewer.selected)
            self.orientation.choices = viewer.state.wcs_only_layers
            self.orientation.selected = self.ref_data.label

        self._reset_default_rotation_options()

    def create_north_up_east_left(self, label="North-up, East-left", set_on_create=False):
        """
        Set the rotation angle and flip to achieve North up and East left
        according to the reference image WCS.
        """
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self.rotation_angle = degn
            self.east_left = True
            self.set_on_create = set_on_create
            self.new_layer_label = label
            self.vue_add_orientation()
        elif set_on_create:
            self.orientation.selected = label

    def create_north_up_east_right(self, label="North-up, East-right", set_on_create=False):
        """
        Set the rotation angle and flip to achieve North up and East right
        according to the reference image WCS.
        """
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self.rotation_angle = 180 - degn
            self.east_left = False
            self.set_on_create = set_on_create
            self.new_layer_label = label
            self.vue_add_orientation()
        elif set_on_create:
            self.orientation.selected = label

    def vue_set_north_up_east_left(self, *args, **kwargs):
        self.create_north_up_east_left(set_on_create=True)

    def vue_set_north_up_east_right(self, *args, **kwargs):
        self.create_north_up_east_right(set_on_create=True)

    def vue_select_default_orientation(self, *args, **kwargs):
        self.orientation.selected = base_wcs_layer_label

    @observe('east_left', 'rotation_angle')
    def _update_layer_label_default(self, event={}):
        self.new_layer_label_default = (
            f'CCW {self.rotation_angle_deg:.2f} ' +
            ('(E-left)' if self.east_left else '(E-right)')
        )
