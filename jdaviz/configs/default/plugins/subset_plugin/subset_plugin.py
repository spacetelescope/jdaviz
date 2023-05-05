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
    'OrState': OrMode,
    'AndState': AndMode,
    'XorState': XorMode,
    'AndNotState': AndNotMode,
    'RangeSubsetState': RangeSubsetState,
    'RoiSubsetState': RoiSubsetState
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
    glue_state_types = List([]).tag(sync=True)
    has_subset_details = Bool(False).tag(sync=True)

    subplugins_opened = Any().tag(sync=True)

    is_centerable = Bool(False).tag(sync=True)

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
        self.subset_states = []

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
        self.glue_state_types = []
        self.is_centerable = False

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

    def _unpack_get_subsets_for_ui(self):
        """
        Convert what app.get_subsets returns into something the UI of this plugin
        can display.

        Returns
        -------

        """
        subset_information = self.app.get_subsets(self.subset_selected, simplify_spectral=False)
        _around_decimals = 6  # Avoid 30 degrees from coming back as 29.999999999999996
        if not subset_information:
            return
        if len(subset_information) == 1:
            self.is_centerable = True
        else:
            self.is_centerable = False

        for spec in subset_information:
            subset_definition = []
            subset_type = ''
            subset_state = spec["subset_state"]
            glue_state = spec["glue_state"]
            if isinstance(subset_state, RoiSubsetState):
                if isinstance(subset_state.roi, CircularROI):
                    x, y = subset_state.roi.get_center()
                    r = subset_state.roi.radius
                    subset_definition = [{"name": "X Center", "att": "xc", "value": x, "orig": x},
                                         {"name": "Y Center", "att": "yc", "value": y, "orig": y},
                                         {"name": "Radius", "att": "radius", "value": r, "orig": r}]

                elif isinstance(subset_state.roi, RectangularROI):
                    for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
                        real_att = att.lower()
                        val = getattr(subset_state.roi, real_att)
                        subset_definition.append(
                            {"name": att, "att": real_att, "value": val, "orig": val})
                    theta = np.around(np.degrees(subset_state.roi.theta), decimals=_around_decimals)
                    subset_definition.append(
                        {"name": "Angle", "att": "theta", "value": theta, "orig": theta})

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

                subset_type = subset_state.roi.__class__.__name__

            elif isinstance(subset_state, RangeSubsetState):
                lo = subset_state.lo
                hi = subset_state.hi
                subset_definition = [{"name": "Lower bound", "att": "lo", "value": lo, "orig": lo},
                                     {"name": "Upper bound", "att": "hi", "value": hi, "orig": hi}]
                subset_type = "Range"
            if len(subset_definition) > 0:
                # Note: .append() does not work for List traitlet.
                self.subset_definitions = self.subset_definitions + [subset_definition]
                self.subset_types = self.subset_types + [subset_type]
                self.glue_state_types = self.glue_state_types + [glue_state]
                self.subset_states = self.subset_states + [subset_state]

    def _get_subset_definition(self, *args):
        """
        Retrieve the parameters defining the selected subset, for example the
        upper and lower bounds for a simple spectral subset.
        """
        self.subset_definitions = []
        self.subset_types = []
        self.glue_state_types = []
        self.subset_states = []

        self._unpack_get_subsets_for_ui()

    def vue_update_subset(self, *args):
        status, reason = self._check_input()
        if not status:
            self.hub.broadcast(SnackbarMessage(reason, color='error', sender=self))
            return

        for index, sub in enumerate(self.subset_definitions):
            if len(self.subset_states) <= index:
                return
            sub_states = self.subset_states[index]
            for d_att in sub:
                if d_att["att"] == 'theta':  # Humans use degrees but glue uses radians
                    d_val = np.radians(d_att["value"])
                else:
                    d_val = float(d_att["value"])

                if float(d_att["orig"]) != d_val:
                    if self.subset_types[index] == "Range":
                        setattr(sub_states, d_att["att"], d_val)
                    else:
                        setattr(sub_states.roi, d_att["att"], d_val)
        try:
            dc = self.data_collection
            subsets = dc.subset_groups
            self.session.edit_subset_mode._combine_data(
                subsets[[x.label for x in subsets].index(self.subset_selected)].subset_state,
                override_mode=ReplaceMode)
        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Failed to update Subset: {repr(err)}", color='error', sender=self))

    def _check_input(self):
        status = True
        reason = ""
        for index, sub in enumerate(self.subset_definitions):
            lo = hi = xmin = xmax = ymin = ymax = None
            for d_att in sub:
                if d_att["att"] == "lo":
                    lo = d_att["value"]
                elif d_att["att"] == "hi":
                    hi = d_att["value"]
                elif d_att["att"] == "radius" and d_att["value"] <= 0:
                    status = False
                    reason = "Failed to update Subset: radius must be a positive scalar"
                    break
                elif d_att["att"] == "xmin":
                    xmin = d_att["value"]
                elif d_att["att"] == "xmax":
                    xmax = d_att["value"]
                elif d_att["att"] == "ymin":
                    ymin = d_att["value"]
                elif d_att["att"] == "ymax":
                    ymax = d_att["value"]

                if lo and hi and hi <= lo:
                    status = False
                    reason = "Failed to update Subset: lower bound must be less than upper bound"
                    break
                elif xmin and xmax and ymin and ymax and (xmax - xmin <= 0 or ymax - ymin <= 0):
                    status = False
                    reason = "Failed to update Subset: width and length must be positive scalars"
                    break

        return status, reason

    def vue_recenter_subset(self, *args):
        # Composite region cannot be centered. This only works for Imviz.
        if not self.is_centerable or self.config != 'imviz':  # no-op
            raise NotImplementedError(
                f'Cannot recenter: is_centerable={self.is_centerable}, config={self.config}')

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
            If Subset is not centerable, this returns `None`.

        Raises
        ------
        NotImplementedError
            Subset type is not supported.

        """
        # Composite region cannot be centered.
        if not self.is_centerable:  # no-op
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

        elif isinstance(subset_state, CompositeSubsetState):
            cen = None

        else:  # pragma: no cover
            raise NotImplementedError(
                f'Getting center of {subset_state.__class__} is not supported')

        return cen

    def set_center(self, new_cen, update=False):
        """Set the desired center for the selected Subset, if applicable.
        If Subset is not centerable, nothing is done.

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
        # Composite region cannot be centered, so just grab first element.
        if not self.is_centerable:  # no-op
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
