import numpy as np
from glue.core.message import EditSubsetMessage, SubsetUpdateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.roi import CircularROI, EllipticalROI, RectangularROI
from glue.core.subset import RoiSubsetState, RangeSubsetState, CompositeSubsetState
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from traitlets import Any, List, Unicode, Bool, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin, SubsetSelect

__all__ = ['SubsetPlugin']

SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


@tray_registry('g-subset-plugin', label="Subset Tools")
class SubsetPlugin(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "subset_plugin.vue"
    select = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("Create New").tag(sync=True)
    mode_selected = Unicode('add').tag(sync=True)
    show_region_info = Bool(True).tag(sync=True)
    subset_types = List([]).tag(sync=True)
    subset_definitions = List([]).tag(sync=True)
    has_subset_details = Bool(False).tag(sync=True)

    subplugins_opened = Any().tag(sync=True)

    is_editable = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.session.hub.subscribe(self, EditSubsetMessage,
                                   handler=self._sync_selected_from_state)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._on_subset_update)

        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          default_text="Create New")

    def _sync_selected_from_state(self, *args):
        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return
        if self.session.edit_subset_mode.edit_subset == []:
            if self.subset_selected != self.subset_select.default_text:
                self.subset_selected = self.subset_select.default_text
                self.show_region_info = False
        else:
            new_label = self.session.edit_subset_mode.edit_subset[0].label
            if new_label != self.subset_selected:
                if new_label not in [s['label'] for s in self.subset_items]:
                    self._sync_available_from_state()
                self.subset_selected = self.session.edit_subset_mode.edit_subset[0].label
                self.show_region_info = True

    def _on_subset_update(self, *args):
        self._sync_selected_from_state(*args)
        if self.subset_selected == 'Create New':
            return
        self._get_subset_definition(*args)
        subset_to_update = self.session.edit_subset_mode.edit_subset[0]
        self.subset_select._update_subset(subset_to_update, attribute="type")

    def _sync_available_from_state(self, *args):
        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return
        self.subset_items = [{'label': self.subset_select.default_text}] + [
                             self.subset_select._subset_to_dict(subset) for subset in
                             self.data_collection.subset_groups]

    @observe('subset_selected')
    def _sync_selected_from_ui(self, change):
        self.subset_definitions = []
        self.subset_types = []
        self.is_editable = False

        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return

        if change['new'] != self.subset_select.default_text:
            self._get_subset_definition(change['new'])
        self.show_region_info = change['new'] != self.subset_select.default_text
        m = [s for s in self.app.data_collection.subset_groups if s.label == change['new']]
        if m != self.session.edit_subset_mode.edit_subset:
            self.session.edit_subset_mode.edit_subset = m

    '''
    # This will be needed once we use a dropdown instead of the actual
    # g-subset-mode component
    @observe("mode_selected")
    def _mode_selected_changed(self, event={}):
        if self.session.edit_subset_mode != self.mode_selected:
            self.session.edit_subset_mode = self.mode_selected
    '''

    def _unpack_nested_subset(self, subset_state):
        '''
        Navigate through the tree of subset states for composite
        subsets made up of multiple regions.
        '''
        if isinstance(subset_state, CompositeSubsetState):
            self._unpack_nested_subset(subset_state.state1)
            self._unpack_nested_subset(subset_state.state2)
            self.is_editable = False
        else:
            if subset_state is not None:
                self._get_subset_subregion_definition(subset_state)

    def _get_subset_subregion_definition(self, subset_state):
        """
        Get the type and parameters for a single region in the subset. Note that
        the string type and operation (if in a composite subset) need to be stored
        separately from the float parameters for display reasons.
        """
        subset_type = ''
        subset_definition = []
        self.is_editable = False
        _around_decimals = 6  # Avoid 30 degrees from coming back as 29.999999999999996

        if isinstance(subset_state, RoiSubsetState):
            if isinstance(subset_state.roi, CircularROI):
                x, y = subset_state.roi.get_center()
                r = subset_state.roi.radius
                subset_definition = [{"name": "X Center", "att": "xc", "value": x, "orig": x},
                                     {"name": "Y Center", "att": "yc", "value": y, "orig": y},
                                     {"name": "Radius", "att": "radius", "value": r, "orig": r}]
                self.is_editable = True

            elif isinstance(subset_state.roi, RectangularROI):
                for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
                    real_att = att.lower()
                    val = getattr(subset_state.roi, real_att)
                    subset_definition.append(
                        {"name": att, "att": real_att, "value": val, "orig": val})
                theta = np.around(np.degrees(subset_state.roi.theta), decimals=_around_decimals)
                subset_definition.append(
                    {"name": "Angle", "att": "theta", "value": theta, "orig": theta})
                self.is_editable = True

            elif isinstance(subset_state.roi, EllipticalROI):
                xc = subset_state.roi.xc
                yc = subset_state.roi.yc
                rx = subset_state.roi.radius_x
                ry = subset_state.roi.radius_y
                theta = np.around(np.degrees(subset_state.roi.theta), decimals=_around_decimals)
                subset_definition = [
                    {"name": "X Center", "att": "xc", "value": xc, "orig": xc},
                    {"name": "Y Center", "att": "yc", "value": yc, "orig": yc},
                    {"name": "X Radius", "att": "radius_x", "value": rx, "orig": rx},
                    {"name": "Y Radius", "att": "radius_y", "value": ry, "orig": ry},
                    {"name": "Angle", "att": "theta", "value": theta, "orig": theta}]
                self.is_editable = True

            subset_type = subset_state.roi.__class__.__name__

        elif isinstance(subset_state, RangeSubsetState):
            lo = subset_state.lo
            hi = subset_state.hi
            subset_definition = [{"name": "Lower bound", "att": "lo", "value": lo, "orig": lo},
                                 {"name": "Upper bound", "att": "hi", "value": hi, "orig": hi}]
            self.is_editable = True
            subset_type = "Range"

        if len(subset_definition) > 0 and subset_definition not in self.subset_definitions:
            # Note: .append() does not work for List traitlet.
            self.subset_definitions = self.subset_definitions + [subset_definition]
            self.subset_types = self.subset_types + [subset_type]

    def _get_subset_definition(self, *args):
        """
        Retrieve the parameters defining the selected subset, for example the
        upper and lower bounds for a simple spectral subset.
        """
        self.subset_definitions = []
        self.subset_types = []

        self._unpack_nested_subset(self.subset_select.selected_subset_state)

    def vue_update_subset(self, *args):
        if not self.is_editable:  # no-op
            return

        subset_state = self.subset_select.selected_subset_state

        # Composite region cannot be edited, so just grab first element.
        subset_type = self.subset_types[0]
        subset_definition = self.subset_definitions[0]

        try:
            if subset_type == "Range":
                sbst_obj = subset_state
            else:
                sbst_obj = subset_state.roi

            for d_att in subset_definition:
                if d_att["att"] == 'theta':  # Humans use degrees but glue uses radians
                    d_val = np.radians(d_att["value"])
                else:
                    d_val = d_att["value"]

                setattr(sbst_obj, d_att["att"], d_val)

            # Force glue to update the Subset. This is the same call used in
            # glue.core.edit_subset_mode.EditSubsetMode.update() but we do not
            # want to deal with all the contract stuff tied to the update() method.
            self.session.edit_subset_mode._combine_data(subset_state, override_mode=ReplaceMode)
        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Failed to update Subset: {repr(err)}", color='error', sender=self))

    def vue_recenter_subset(self, *args):
        # Composite region cannot be edited. This only works for Imviz.
        if not self.is_editable or self.config != 'imviz':  # no-op
            raise NotImplementedError(
                f'Cannot recenter: is_editable={self.is_editable}, config={self.config}')

        from photutils.aperture import ApertureStats
        from jdaviz.core.region_translators import regions2aperture, _get_region_from_spatial_subset

        try:
            reg = _get_region_from_spatial_subset(self, self.subset_selected)
            aperture = regions2aperture(reg)
            data = self.dataset.selected_dc_item
            comp = data.get_component(data.main_components[0])
            comp_data = comp.data
            phot_aperstats = ApertureStats(comp_data, aperture)

            # Centroid was calculated in selected data, which might or might not be
            # the reference data. However, Subset is always defined w.r.t.
            # the reference data, so we need to convert back.
            viewer = self.app._jdaviz_helper.default_viewer
            x, y, _, _ = viewer._get_real_xy(
                data, phot_aperstats.xcentroid, phot_aperstats.ycentroid, reverse=True)
            if not np.all(np.isfinite((x, y))):
                raise ValueError(f'Invalid centroid ({x}, {y})')
        except Exception as err:
            self.set_center(self.get_center(), update=False)
            self.hub.broadcast(SnackbarMessage(
                f"Failed to calculate centroid: {repr(err)}", color='error', sender=self))
        else:
            self.set_center((x, y), update=True)

    def get_center(self):
        """Return the center of the Subset.
        This may or may not be the centroid obtain from data.

        Returns
        -------
        cen : number, tuple of numbers, or `None`
            The center of the Subset in ``x`` or ``(x, y)``,
            depending on the Subset type, if applicable.
            If Subset is not editable, this returns `None`.

        Raises
        ------
        NotImplementedError
            Subset type is not supported.

        """
        # Composite region cannot be edited.
        if not self.is_editable:  # no-op
            return

        subset_state = self.subset_select.selected_subset_state

        if isinstance(subset_state, RoiSubsetState):
            sbst_obj = subset_state.roi
            if isinstance(sbst_obj, (CircularROI, EllipticalROI)):
                cen = sbst_obj.get_center()
            elif isinstance(sbst_obj, RectangularROI):
                cen = sbst_obj.center()
            else:  # pragma: no cover
                raise NotImplementedError(
                    f'Getting center of {sbst_obj.__class__} is not supported')

        elif isinstance(subset_state, RangeSubsetState):
            cen = (subset_state.hi - subset_state.lo) * 0.5 + subset_state.lo

        else:  # pragma: no cover
            raise NotImplementedError(
                f'Getting center of {subset_state.__class__} is not supported')

        return cen

    def set_center(self, new_cen, update=False):
        """Set the desired center for the selected Subset, if applicable.
        If Subset is not editable, nothing is done.

        Parameters
        ----------
        new_cen : number or tuple of numbers
            The new center defined either as ``x`` or ``(x, y)``,
            depending on the Subset type.

        update : bool
            If `True`, the Subset is also moved to the new center.
            Otherwise, only the relevant editable fields are updated but the
            Subset is not moved.

        Raises
        ------
        NotImplementedError
            Subset type is not supported.

        """
        # Composite region cannot be edited, so just grab first element.
        if not self.is_editable:  # no-op
            return

        subset_state = self.subset_select.selected_subset_state

        if isinstance(subset_state, RoiSubsetState):
            x, y = new_cen
            sbst_obj = subset_state.roi
            if isinstance(sbst_obj, (CircularROI, EllipticalROI)):
                self._set_value_in_subset_definition(0, "X Center", "value", x)
                self._set_value_in_subset_definition(0, "Y Center", "value", y)
            elif isinstance(sbst_obj, RectangularROI):
                cx, cy = sbst_obj.center()
                dx = x - cx
                dy = y - cy
                self._set_value_in_subset_definition(0, "Xmin", "value", sbst_obj.xmin + dx)
                self._set_value_in_subset_definition(0, "Xmax", "value", sbst_obj.xmax + dx)
                self._set_value_in_subset_definition(0, "Ymin", "value", sbst_obj.ymin + dy)
                self._set_value_in_subset_definition(0, "Ymax", "value", sbst_obj.ymax + dy)
            else:  # pragma: no cover
                raise NotImplementedError(f'Recentering of {sbst_obj.__class__} is not supported')

        elif isinstance(subset_state, RangeSubsetState):
            dx = new_cen - ((subset_state.hi - subset_state.lo) * 0.5 + subset_state.lo)
            self._set_value_in_subset_definition(0, "Lower bound", "value", subset_state.lo + dx)
            self._set_value_in_subset_definition(0, "Upper bound", "value", subset_state.hi + dx)

        else:  # pragma: no cover
            raise NotImplementedError(
                f'Getting center of {subset_state.__class__} is not supported')

        if update:
            self.vue_update_subset()
        else:
            # Force UI to update on browser without changing the subset.
            tmp = self.subset_definitions
            self.subset_definitions = []
            self.subset_definitions = tmp

    # List of JSON-like dict is nice for front-end but a pain to look up,
    # so we use these helper functions.

    def _get_value_from_subset_definition(self, index, name, desired_key):
        subset_definition = self.subset_definitions[index]
        value = None
        for item in subset_definition:
            if item['name'] == name:
                value = item[desired_key]
                break
        return value

    def _set_value_in_subset_definition(self, index, name, desired_key, new_value):
        for i in range(len(self.subset_definitions[index])):
            if self.subset_definitions[index][i]['name'] == name:
                self.subset_definitions[index][i]['value'] = new_value
                break
