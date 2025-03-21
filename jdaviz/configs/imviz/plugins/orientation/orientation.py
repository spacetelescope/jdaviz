from astropy import units as u
from astropy.wcs.wcsapi import BaseHighLevelWCS
from glue.core.link_helpers import LinkSame
from glue.core.message import (
    DataCollectionAddMessage, SubsetCreateMessage, SubsetDeleteMessage
)
from glue.core.subset import Subset
from glue.core.subset_group import GroupedSubset
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, NoAffineApproximation
from glue.viewers.image.state import ImageSubsetLayerState
from traitlets import List, Unicode, Bool, Dict, observe

from jdaviz.configs.imviz.wcs_utils import (
    get_compass_info, _get_rotated_nddata_from_label
)
from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import (
    ExitBatchLoadMessage, ChangeRefDataMessage,
    AstrowidgetMarkersChangedMessage, MarkersPluginUpdate,
    SnackbarMessage, ViewerAddedMessage, AddDataMessage, LinkUpdatedMessage
)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin, SelectPluginComponent, LayerSelect, ViewerSelectMixin, AutoTextField
)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import (get_wcs_only_layer_labels, get_reference_image_data,
                          layer_is_2d, _wcs_only_label)

__all__ = ['Orientation']

orientation_plugin_label = "Orientation"
base_wcs_layer_label = 'Default orientation'
align_by_msg_to_trait = {'pixels': 'Pixels', 'wcs': 'WCS'}


@tray_registry('imviz-orientation', label=orientation_plugin_label, viewer_requirements="image")
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
    * ``align_by`` (`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``wcs_fast_approximation``
    * :meth:`delete_subsets`
    * ``viewer``
    * ``orientation``
    * ``rotation_angle``
    * ``east_left``
    * :meth:`add_orientation`
    * :meth:`set_north_up_east_left`
    * :meth:`set_north_up_east_right`
    """
    template_file = __file__, "orientation.vue"

    # defined as traitlet in addition to global variable above to
    # allow access from UI - leave fixed
    base_wcs_layer_label = Unicode(base_wcs_layer_label).tag(sync=True)

    align_by_items = List().tag(sync=True)
    align_by_selected = Unicode().tag(sync=True)
    wcs_use_fallback = Bool(True).tag(sync=True)
    wcs_fast_approximation = Bool(True).tag(sync=True)
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

        # description displayed under plugin title in tray
        self._plugin_description = 'Rotate viewer orientation and choose alignment (pixel or sky).'

        self.icons = {k: v for k, v in self.app.state.icons.items()}

        self.align_by = SelectPluginComponent(self,
                                              items='align_by_items',
                                              selected='align_by_selected',
                                              manual_options=['Pixels', 'WCS'])

        self.orientation = LayerSelect(
            self, 'orientation_layer_items', 'orientation_layer_selected', 'viewer_selected',
            'multiselect', only_wcs_layers=True
        )
        self.orientation_layer_label = AutoTextField(
            self, 'new_layer_label', 'new_layer_label_default', 'new_layer_label_auto', None
        )

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
                'align_by', 'wcs_fast_approximation',
                'delete_subsets', 'viewer', 'orientation',
                'rotation_angle', 'east_left', 'add_orientation',
                'set_north_up_east_left', 'set_north_up_east_right',
            )
        )

    def _link_image_data(self):
        self.linking_in_progress = True
        try:
            align_by = self.align_by.selected.lower()
            link_image_data(
                self.app,
                align_by=align_by,
                wcs_fallback_scheme='pixels' if self.wcs_use_fallback else None,
                wcs_fast_approximation=self.wcs_fast_approximation,
                error_on_fail=False)
        except Exception:  # pragma: no cover
            raise
        else:
            # Only broadcast after success.
            self.app.hub.broadcast(LinkUpdatedMessage(
                align_by, self.wcs_use_fallback, self.wcs_fast_approximation, sender=self.app))
        finally:
            self.linking_in_progress = False

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

    @observe('align_by_selected', 'wcs_use_fallback', 'wcs_fast_approximation')
    def _update_link(self, msg={}):
        """Run link_image_data with the selected parameters."""
        if not hasattr(self, 'align_by'):
            # could happen before plugin is fully initialized
            return

        if msg.get('name', None) == 'wcs_fast_approximation' and self.align_by.selected == 'Pixels':  # noqa
            # approximation doesn't apply, avoid updating when not necessary!
            return

        if self.linking_in_progress:
            return

        self.linking_in_progress = True  # Prevent recursion

        if self.need_clear_subsets:
            self.linking_in_progress = False
            raise ValueError("Link type can only be changed after existing subsets "
                             f"are deleted, but {len(self.app.data_collection.subset_groups)} "
                             f"subset(s) still exist. To delete them, you can use "
                             f"`delete_subsets()` from the plugin API.")

        if self.need_clear_astrowidget_markers:
            setattr(self, msg.get('name'), msg.get('old'))
            self.linking_in_progress = False
            raise ValueError(f"cannot change linking with markers present (value reverted to "
                             f"'{msg.get('old')}'), call viewer.reset_markers()")

        if self.align_by.selected == 'Pixels':
            self.wcs_fast_approximation = True

        self._link_image_data()
        # NOTE: _link_image_data will reset linking_in_progress to False

        # load data into the viewer that are now compatible with the
        # new link type, remove data from the viewer that are now
        # incompatible:
        wcs_linked = self.align_by.selected == 'WCS'
        viewer_selected = self.app.get_viewer(self.viewer.selected)

        data_in_viewer = self.app.get_viewer(viewer_selected.reference).data()

        for data in self.app.data_collection:
            is_wcs_only = data.meta.get(_wcs_only_label, False)
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

        self._update_layer_label_default()

        # Clear previous zoom limits because they no longer mean anything.
        for v in self.app._viewer_store.values():
            v._prev_limits = None

    def _on_subset_change(self, msg):
        self.need_clear_subsets = len(self.app.data_collection.subset_groups) > 0

    def delete_subsets(self):
        """
        Delete all subsets app-wide.  Required before changing ``align_by``.
        """
        # subsets will be deleted on changing link type:
        self.app.delete_subsets()

    def vue_delete_subsets(self, *args):
        self.delete_subsets()

    def vue_reset_astrowidget_markers(self, *args):
        for viewer in self.app._viewer_store.values():
            viewer.reset_markers()

    def _get_wcs_angles(self, first_loaded_image=None):
        if first_loaded_image is None:
            first_loaded_image = self.viewer.selected_obj.first_loaded_data
            if first_loaded_image is None:
                # These won't end up getting used in this case, but we need an actual number
                return 0, 0, 0
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
        self._add_orientation(rotation_angle=rotation_angle, east_left=east_left, label=label,
                              set_on_create=set_on_create, wrt_data=wrt_data)

    def _add_orientation(self, rotation_angle=None, east_left=None, label=None,
                         set_on_create=True, wrt_data=None, from_ui=False):

        if self.align_by_selected != 'WCS':
            raise ValueError("must be aligned by WCS to add orientation options")

        if wrt_data is None:
            # if not specified, use first-loaded image layer as the
            # default rotation:
            wrt_data = self.viewer.selected_obj.first_loaded_data
            if wrt_data is None:  # Nothing in viewer
                msg = "Viewer must have data loaded to add an orientation."
                if from_ui:
                    self.hub.broadcast(SnackbarMessage(msg, color="error",
                                                       timeout=6000, sender=self))
                else:
                    raise ValueError(msg)
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
            # Not sure why this is sometimes missing, but we can add it here
            if label not in self.orientation.choices:
                self.orientation.choices += [label]
            self.orientation.selected = label

    def _add_data_to_viewer(self, data_label, viewer_id):
        viewer = self.app.get_viewer_by_id(viewer_id)

        if data_label not in viewer.data_menu.orientation.choices:
            self.app.add_data_to_viewer(viewer_id, data_label)

    def _on_viewer_added(self, msg):
        self._send_wcs_layers_to_all_viewers(viewers_to_update=[msg._viewer_id])

    @observe('viewer_items')
    def _send_wcs_layers_to_all_viewers(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            return

        wcs_only_layers = get_wcs_only_layer_labels(self.app)

        viewers_to_update = kwargs.get(
            'viewers_to_update', self.app._viewer_store.keys()
        )
        for viewer_ref in viewers_to_update:
            viewer_dm = self.app._jdaviz_helper.viewers.get(viewer_ref).data_menu
            for wcs_layer in wcs_only_layers:
                if wcs_layer not in self.viewer.selected_obj.layers:
                    self.app.add_data_to_viewer(viewer_ref, wcs_layer)
            if (
                self.orientation.selected not in
                    wcs_only_layers and
                    self.align_by_selected == 'WCS'
            ):
                viewer_dm.orientation.selected = base_wcs_layer_label

    def _on_data_add_to_viewer(self, msg):
        all_wcs_only_layers = all(
            layer.layer.meta.get(_wcs_only_label)
            for layer in self.viewer.selected_obj.layers
            if hasattr(layer.layer, "meta")
        )
        if all_wcs_only_layers and msg.data.meta.get(_wcs_only_label, False):
            # on adding first data layer, reset the limits:
            self.viewer.selected_obj.state.reset_limits()

    def vue_add_orientation(self, *args, **kwargs):
        self._add_orientation(set_on_create=True, from_ui=True)

    def set_orientation_for_viewer(self, orientation, viewer_id):
        if self._refdata_change_available:
            self.app._change_reference_data(
                orientation, viewer_id=viewer_id
            )
            viewer_item = self.app._viewer_item_by_id(viewer_id)
            if viewer_item['reference_data_label'] != orientation:
                viewer_item['reference_data_label'] = orientation

    @observe('orientation_layer_selected')
    def _change_reference_data(self, *args, **kwargs):
        self.set_orientation_for_viewer(self.orientation.selected, self.viewer.selected)

    def _on_refdata_change(self, msg):

        if hasattr(self, 'viewer'):
            ref_data = self.ref_data
            viewer = self.viewer.selected_obj

            # don't select until reference data are available:
            if ref_data is not None:
                align_by = viewer.get_alignment_method(ref_data.label)
                if align_by != 'self':
                    self.align_by_selected = align_by_msg_to_trait[align_by]
            elif not len(viewer.data()):
                self.align_by_selected = align_by_msg_to_trait['pixels']

            if msg.data.label not in self.orientation.choices:
                return

            if msg.viewer_id == self.viewer.selected:
                self.orientation.selected = msg.data.label

            # we never want to highlight subsets of pixels within WCS-only layers,
            # so if this layer is an ImageSubsetLayerState on a WCS-only layer,
            # ensure that it is never visible:
            for layer in viewer.state.layers:
                if (
                    isinstance(layer.layer, ImageSubsetLayerState) and
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

    def _set_north_up_east_left(self, label="North-up, East-left", set_as_orientation=False,
                                from_ui=False):
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self._add_orientation(rotation_angle=degn, east_left=True,
                                  label=label, set_on_create=set_as_orientation,
                                  from_ui=from_ui)
        elif set_as_orientation:
            self.orientation.selected = label

    def set_north_up_east_left(self, label="North-up, East-left"):
        """
        Set (and create if necessary) the rotation angle and flip to achieve North up
        and East left according to the reference image WCS.

        Parameters
        ----------
        label : str
            Data label for the orientation layer.  If already exists, will be set as the
            current orientation layer according to ``set_as_orientation``.  Otherwise,
            a new layer will be created with this label.
        """
        self._set_north_up_east_left(label=label, set_as_orientation=True)

    def _set_north_up_east_right(self, label="North-up, East-right", set_as_orientation=False,
                                 from_ui=False):
        if label not in self.orientation.choices:
            degn = self._get_wcs_angles()[-3]
            self._add_orientation(rotation_angle=180 - degn, east_left=False,
                                  label=label, set_on_create=set_as_orientation,
                                  from_ui=from_ui)
        elif set_as_orientation:
            self.orientation.selected = label

    def set_north_up_east_right(self, label="North-up, East-right"):
        """
        Set (and create, if necessary) the rotation angle and flip to achieve North up
        and East right according to the reference image WCS.

        Parameters
        ----------
        label : str
            Data label for the orientation layer.  If already exists, will be set as the
            current orientation layer according to ``set_as_orientation``.  Otherwise,
            a new layer will be created with this label.
        """
        self._set_north_up_east_right(label=label, set_as_orientation=True)

    def vue_select_north_up_east_left(self, *args, **kwargs):
        self._set_north_up_east_left(set_as_orientation=True, from_ui=True)

    def vue_select_north_up_east_right(self, *args, **kwargs):
        self._set_north_up_east_right(set_as_orientation=True, from_ui=True)

    def vue_select_default_orientation(self, *args, **kwargs):
        self.orientation.selected = base_wcs_layer_label

    @observe('east_left', 'rotation_angle')
    def _update_layer_label_default(self, event={}):
        self.new_layer_label_default = (
            f'CCW {self.rotation_angle_deg():.2f} ' +
            ('(E-left)' if self.east_left else '(E-right)')
        )


def link_image_data(app, align_by='pixels', wcs_fallback_scheme=None, wcs_fast_approximation=True,
                    error_on_fail=False):
    """(Re)link loaded data in Imviz with the desired link type.

    .. note::

        Any markers added in Imviz will need to be removed manually before changing linking type.
        You can add back the markers using
        :meth:`~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin.add_markers`
        for the relevant viewer(s).

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        Application associated with Imviz, e.g., ``imviz.app``.

    align_by : {'pixels', 'wcs'}
        Choose to link by pixels or WCS.

    wcs_fallback_scheme : {None, 'pixels'}
        If WCS linking failed, choose to fall back to linking by pixels or not at all.
        This is only used when ``align_by='wcs'``.
        Choosing `None` may result in some Imviz functionality not working properly.

    wcs_fast_approximation : bool
        Use an affine transform to represent the offset between images if possible
        (requires that the approximation is accurate to within 1 pixel with the
        full WCS transformations). If approximation fails, it will automatically
        fall back to full WCS transformation. This is only used when ``align_by='wcs'``.
        Affine approximation is much more performant at the cost of accuracy.

    error_on_fail : bool
        If `True`, any failure in linking will raise an exception.
        If `False`, warnings will be emitted as snackbar messages.
        When only warnings are emitted and no links are assigned,
        some Imviz functionality may not work properly.

    Raises
    ------
    ValueError
        Invalid inputs or reference data.

    """
    if len(app.data_collection) <= 1 and align_by != 'wcs':  # No need to link, we are done.
        return

    if align_by not in ('pixels', 'wcs'):  # pragma: no cover
        raise ValueError(f"align_by must be 'pixels' or 'wcs', got {align_by}")
    if align_by == 'wcs' and wcs_fallback_scheme not in (None, 'pixels'):  # pragma: no cover
        raise ValueError("wcs_fallback_scheme must be None or 'pixels', "
                         f"got {wcs_fallback_scheme}")
    if align_by == 'wcs':
        at_least_one_data_have_wcs = len([
            hasattr(d, 'coords') and isinstance(d.coords, BaseHighLevelWCS)
            for d in app.data_collection
        ]) > 0
        if not at_least_one_data_have_wcs:  # pragma: no cover
            if wcs_fallback_scheme is None:
                if error_on_fail:
                    raise ValueError("align_by can only be 'wcs' when wcs_fallback_scheme "
                                     "is 'None' if at least one image has a valid WCS.")
                else:
                    return
            else:
                # fall back on pixel linking
                align_by = 'pixels'

    old_align_by = getattr(app, '_align_by', None)

    # In WCS linking, changing orientation layer is done within Orientation plugin,
    # so here we assume viewer.state.reference_data is already the desired
    # orientation by the time this function is called.
    #
    # In pixels linking, Affine approximation does not matter.
    #
    # data1 = reference, data2 = actual data
    data_already_linked = []
    if (align_by == old_align_by and
            (align_by == "pixels" or wcs_fast_approximation == app._wcs_fast_approximation)):
        # We are only here to link new data with existing configuration,
        # so no need to relink existing data.
        for link in app.data_collection.external_links:
            data_already_linked.append(link.data2)
    else:  # pragma: no cover
        # Everything has to be relinked.
        for viewer in app._viewer_store.values():
            if len(viewer._marktags):
                raise ValueError(f"cannot change align_by (from '{app._align_by}' to "
                                 f"'{align_by}') when markers are present. "
                                 f" Clear markers with viewer.reset_markers() first")

    # set internal tracking of align_by before changing reference data for anything that is
    # subscribed to a change in reference data
    app._align_by = align_by
    app._wcs_fast_approximation = wcs_fast_approximation

    # wcs -> pixels: First loaded real data will be reference.
    if align_by == 'pixels' and old_align_by == 'wcs':
        # default reference layer is the first-loaded image in default viewer:
        refdata = app._jdaviz_helper.default_viewer._obj.first_loaded_data
        if refdata is None:  # No data in viewer, just use first in collection  # pragma: no cover
            iref = 0
            refdata = app.data_collection[iref]
        else:
            iref = app.data_collection.index(refdata)

        # set default layer to reference data in all viewers:
        for viewer_id in app.get_viewer_ids():
            app._change_reference_data(refdata.label, viewer_id=viewer_id)

    # pixels -> wcs: Always the default orientation
    elif align_by == 'wcs' and old_align_by == 'pixels':
        # Have to create the default orientation first.
        if base_wcs_layer_label not in app.data_collection.labels:
            default_reference_layer = (app._jdaviz_helper.default_viewer._obj.first_loaded_data
                                       or app.data_collection[0])
            degn = get_compass_info(default_reference_layer.coords, default_reference_layer.shape)[-3]  # noqa: E501
            # Default rotation is the same orientation as the original reference data:
            rotation_angle = -degn * u.deg
            ndd = _get_rotated_nddata_from_label(app, default_reference_layer.label, rotation_angle)
            app._jdaviz_helper.load_data(ndd, base_wcs_layer_label)

        # set default layer to reference data in all viewers:
        for viewer_id in app.get_viewer_ids():
            app._change_reference_data(base_wcs_layer_label, viewer_id=viewer_id)

        refdata = app.data_collection[base_wcs_layer_label]
        iref = app.data_collection.index(refdata)

    # Re-use current reference data.
    else:
        refdata, iref = get_reference_image_data(app)
        # App just loaded, nothing yet, so take first image.
        if refdata is None:
            refdata = app._jdaviz_helper.default_viewer._obj.first_loaded_data
            if refdata is None:  # No data in viewer, just use first in collection
                iref = 0
                refdata = app.data_collection[iref]
            else:   # pragma: no cover
                iref = app.data_collection.index(refdata)

    # With reference data changed, if needed, now we relink as needed.

    links_list = []
    ids0 = refdata.pixel_component_ids
    ndim_range = range(2)  # We only support 2D

    for i, data in enumerate(app.data_collection):
        # 1. Do not link with self.
        # 2. We are not touching any existing Subsets or Table. They keep their own links.
        # 3. Links already exist for this entry and we're not changing the type.
        # 4. We are not touching fake WCS layers in pixel linking.
        # 5. We are not touching data without WCS in WCS linking.
        if ((i == iref) or (not layer_is_2d(data)) or (data in data_already_linked) or
                (align_by == "pixels" and data.meta.get(_wcs_only_label)) or
                (align_by == "wcs" and not hasattr(data.coords, 'pixel_to_world'))):
            continue

        ids1 = data.pixel_component_ids
        new_links = []
        try:
            if align_by == 'pixels':
                new_links = [LinkSame(ids0[i], ids1[i]) for i in ndim_range]
            else:  # wcs
                wcslink = WCSLink(data1=refdata, data2=data, cids1=ids0, cids2=ids1)
                if wcs_fast_approximation:
                    try:
                        new_links = [wcslink.as_affine_link()]
                    except NoAffineApproximation:  # pragma: no cover
                        new_links = [wcslink]
                else:
                    new_links = [wcslink]
        except Exception as e:  # pragma: no cover
            if align_by == 'wcs' and wcs_fallback_scheme == 'pixels':
                try:
                    new_links = [LinkSame(ids0[i], ids1[i]) for i in ndim_range]
                except Exception as e:  # pragma: no cover
                    if error_on_fail:
                        raise
                    else:
                        app.hub.broadcast(SnackbarMessage(
                            f"Error linking '{data.label}' to '{refdata.label}': "
                            f"{repr(e)}", color="warning", timeout=8000, sender=app))
                        continue
            else:  # pragma: no cover
                if error_on_fail:
                    raise
                else:
                    app.hub.broadcast(SnackbarMessage(
                        f"Error linking '{data.label}' to '{refdata.label}': "
                        f"{repr(e)}", color="warning", timeout=8000, sender=app))
                    continue
        links_list += new_links

    if len(links_list) > 0:
        with app.data_collection.delay_link_manager_update():
            if len(data_already_linked):
                app.data_collection.add_link(links_list)  # Add to existing
            else:
                app.data_collection.set_links(links_list)  # Redo all links

        app.hub.broadcast(SnackbarMessage(
            'Images successfully relinked', color='success', timeout=8000, sender=app))

    for viewer in app._viewer_store.values():
        wcs_linked = align_by == 'wcs'
        # viewer-state needs to know link type for reset_limits behavior
        viewer.state.linked_by_wcs = wcs_linked
        # also need to store a copy in the viewer item for the data dropdown to access
        viewer_item = app._get_viewer_item(viewer.reference)

        viewer_item['reference_data_label'] = refdata.label
        viewer_item['linked_by_wcs'] = wcs_linked

        # if changing from one link type to another, reset the limits:
        if align_by != old_align_by:
            viewer.state.reset_limits()
