import os

import numpy as np

from astropy.time import Time
import astropy.units as u
from glue.core.message import EditSubsetMessage, SubsetUpdateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.roi import CircularROI, CircularAnnulusROI, EllipticalROI, RectangularROI
from glue.core.subset import RoiSubsetState, RangeSubsetState, CompositeSubsetState
from glue.icons import icon_path
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Any, List, Unicode, Bool, observe

from jdaviz.core.events import SnackbarMessage, GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin, SubsetSelect
from jdaviz.core.tools import ICON_DIR
from jdaviz.utils import MultiMaskSubsetState

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
    subset_selected = Any().tag(sync=True)

    mode_selected = Unicode('add').tag(sync=True)
    show_region_info = Bool(True).tag(sync=True)
    subset_types = List([]).tag(sync=True)
    subset_definitions = List([]).tag(sync=True)
    glue_state_types = List([]).tag(sync=True)
    has_subset_details = Bool(False).tag(sync=True)

    subplugins_opened = Any().tag(sync=True)

    multiselect = Bool(False).tag(sync=True)  # multiselect only for subset
    is_centerable = Bool(False).tag(sync=True)
    can_simplify = Bool(False).tag(sync=True)
    can_freeze = Bool(False).tag(sync=True)

    icon_replace = Unicode(read_icon(os.path.join(icon_path("glue_replace", icon_format="svg")), 'svg+xml')).tag(sync=True)  # noqa
    icon_or = Unicode(read_icon(os.path.join(icon_path("glue_or", icon_format="svg")), 'svg+xml')).tag(sync=True)  # noqa
    icon_and = Unicode(read_icon(os.path.join(icon_path("glue_and", icon_format="svg")), 'svg+xml')).tag(sync=True)  # noqa
    icon_xor = Unicode(read_icon(os.path.join(icon_path("glue_xor", icon_format="svg")), 'svg+xml')).tag(sync=True)  # noqa
    icon_andnot = Unicode(read_icon(os.path.join(icon_path("glue_andnot", icon_format="svg")), 'svg+xml')).tag(sync=True)  # noqa

    icon_radialtocheck = Unicode(read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml')).tag(sync=True)  # noqa
    icon_checktoradial = Unicode(read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.session.hub.subscribe(self, EditSubsetMessage,
                                   handler=self._sync_selected_from_state)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._on_subset_update)
        self.session.hub.subscribe(self, GlobalDisplayUnitChanged,
                                   handler=self._on_display_unit_changed)

        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          multiselect='multiselect',
                                          default_text="Create New")
        self.subset_states = []
        self.spectral_display_unit = None

    def _sync_selected_from_state(self, *args):
        if not hasattr(self, 'subset_select') or self.multiselect:
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
        if 'Create New' in self.subset_selected:
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

    def _unpack_get_subsets_for_ui(self):
        """
        Convert what app.get_subsets returns into something the UI of this plugin
        can display.
        """
        if self.multiselect:
            self.is_centerable = True
            return

        subset_information = self.app.get_subsets(self.subset_selected,
                                                  simplify_spectral=False,
                                                  use_display_units=True)
        _around_decimals = 6  # Avoid 30 degrees from coming back as 29.999999999999996
        if not subset_information:
            return
        if ((len(subset_information) == 1) and
                (isinstance(subset_information[0]["subset_state"], RangeSubsetState) or
                 (isinstance(subset_information[0]["subset_state"], RoiSubsetState) and
                  isinstance(subset_information[0]["subset_state"].roi,
                             (CircularROI, RectangularROI, EllipticalROI))))):
            self.is_centerable = True
        else:
            self.is_centerable = False

        for spec in subset_information:
            subset_definition = []
            subset_type = ''
            subset_state = spec["subset_state"]
            glue_state = spec["glue_state"]
            if isinstance(subset_state, RoiSubsetState):
                subset_definition.append({
                    "name": "Parent", "att": "parent",
                    "value": subset_state.xatt.parent.label,
                    "orig": subset_state.xatt.parent.label})

                if isinstance(subset_state.roi, CircularROI):
                    x, y = subset_state.roi.center()
                    r = subset_state.roi.radius
                    subset_definition += [
                        {"name": "X Center", "att": "xc", "value": x, "orig": x},
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
                    xc, yc = subset_state.roi.center()
                    rx = subset_state.roi.radius_x
                    ry = subset_state.roi.radius_y
                    theta = np.around(np.degrees(subset_state.roi.theta), decimals=_around_decimals)
                    subset_definition += [
                        {"name": "X Center", "att": "xc", "value": xc, "orig": xc},
                        {"name": "Y Center", "att": "yc", "value": yc, "orig": yc},
                        {"name": "X Radius", "att": "radius_x", "value": rx, "orig": rx},
                        {"name": "Y Radius", "att": "radius_y", "value": ry, "orig": ry},
                        {"name": "Angle", "att": "theta", "value": theta, "orig": theta}]

                elif isinstance(subset_state.roi, CircularAnnulusROI):
                    x, y = subset_state.roi.center()
                    inner_r = subset_state.roi.inner_radius
                    outer_r = subset_state.roi.outer_radius
                    subset_definition += [{"name": "X Center", "att": "xc", "value": x, "orig": x},
                                          {"name": "Y Center", "att": "yc", "value": y, "orig": y},
                                          {"name": "Inner radius", "att": "inner_radius",
                                           "value": inner_r, "orig": inner_r},
                                          {"name": "Outer radius", "att": "outer_radius",
                                           "value": outer_r, "orig": outer_r}]

                subset_type = subset_state.roi.__class__.__name__

            elif isinstance(subset_state, RangeSubsetState):
                region = spec['region']
                if isinstance(region, Time):
                    lo = region.min()
                    hi = region.max()
                    subset_definition = [{"name": "Lower bound", "att": "lo", "value": lo.value,
                                          "orig": lo.value},
                                         {"name": "Upper bound", "att": "hi", "value": hi.value,
                                          "orig": hi.value}]
                else:
                    lo = region.lower
                    hi = region.upper
                    subset_definition = [{"name": "Lower bound", "att": "lo", "value": lo.value,
                                          "orig": lo.value, "unit": str(lo.unit)},
                                         {"name": "Upper bound", "att": "hi", "value": hi.value,
                                          "orig": hi.value, "unit": str(hi.unit)}]
                subset_type = "Range"

            elif isinstance(subset_state, MultiMaskSubsetState):
                total_masked = subset_state.total_masked_first_data()
                subset_definition = [{"name": "Masked values", "att": "masked",
                                      "value": total_masked,
                                      "orig": total_masked}]
                subset_type = "Mask"
            if len(subset_definition) > 0:
                # Note: .append() does not work for List traitlet.
                self.subset_definitions = self.subset_definitions + [subset_definition]
                self.subset_types = self.subset_types + [subset_type]
                self.glue_state_types = self.glue_state_types + [glue_state]
                self.subset_states = self.subset_states + [subset_state]

        simplifiable_states = set(['AndState', 'XorState', 'AndNotState'])
        # Check if the subset has more than one subregion, is a range subset type, and
        # uses one of the states that can be simplified. Mask subset types cannot be simplified
        # so subsets contained that are skipped.
        if 'Mask' in self.subset_types:
            self.can_simplify = False
        elif (len(self.subset_states) > 1 and isinstance(self.subset_states[0], RangeSubsetState)
                and len(simplifiable_states - set(self.glue_state_types)) < 3):
            self.can_simplify = True
        elif (len(self.subset_states) > 1 and isinstance(self.subset_states[0], RangeSubsetState)
              and self.app.is_there_overlap_spectral_subset(self.subset_selected)):
            self.can_simplify = True
        else:
            self.can_simplify = False

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

    def vue_freeze_subset(self, *args):
        sgs = {sg.label: sg for sg in self.app.data_collection.subset_groups}
        sg = sgs.get(self.subset_selected)

        masks = {}
        for data in self.app.data_collection:
            masks[data.uuid] = sg.subset_state.to_mask(data)

        sg.subset_state = MultiMaskSubsetState(masks)

    def vue_simplify_subset(self, *args):
        if self.multiselect:
            self.hub.broadcast(SnackbarMessage("Cannot simplify spectral subset "
                                               "when multiselect is active", color='warning',
                                               sender=self))
            return
        if len(self.subset_states) < 2:
            self.hub.broadcast(SnackbarMessage("Cannot simplify spectral subset "
                                               "of length less than 2", color='warning',
                                               sender=self))
            return
        att = self.subset_states[0].att
        self.app.simplify_spectral_subset(subset_name=self.subset_selected, att=att,
                                          overwrite=True)

    def _on_display_unit_changed(self, msg):
        # We only care about the spectral units, since flux units don't affect spectral subsets
        if msg.axis == "spectral":
            self.spectral_display_unit = msg.unit
            if self.subset_selected != self.subset_select.default_text:
                self._get_subset_definition(self.subset_selected)

    def vue_update_subset(self, *args):
        if self.multiselect:
            self.hub.broadcast(SnackbarMessage("Cannot update subset "
                                               "when multiselect is active", color='warning',
                                               sender=self))
            return

        status, reason = self._check_input()
        if not status:
            self.hub.broadcast(SnackbarMessage(reason, color='error', sender=self))
            return

        for index, sub in enumerate(self.subset_definitions):
            if len(self.subset_states) <= index:
                return
            sub_states = self.subset_states[index]
            for d_att in sub:
                if d_att["att"] == 'parent':  # Read-only
                    continue

                if d_att["att"] == 'theta':  # Humans use degrees but glue uses radians
                    d_val = np.radians(d_att["value"])
                else:
                    d_val = float(d_att["value"])

                # Convert from display unit to original unit if necessary
                if self.subset_types[index] == "Range":
                    if self.spectral_display_unit is not None:
                        x_att = sub_states.att
                        base_units = self.app.data_collection[0].get_component(x_att).units
                        if self.spectral_display_unit != base_units:
                            d_val = d_val*u.Unit(self.spectral_display_unit)
                            d_val = d_val.to(u.Unit(base_units))
                            d_val = d_val.value

                if float(d_att["orig"]) != d_val:
                    if self.subset_types[index] == "Range":
                        setattr(sub_states, d_att["att"], d_val)
                    else:
                        setattr(sub_states.roi, d_att["att"], d_val)
        self._push_update_to_ui()

    def _push_update_to_ui(self, subset_name=None):
        """
        Forces the UI to update how it represents the subset.

        Parameters
        ----------
        subset_name : str
            The name of the subset that is being updated.

        """
        if not subset_name:
            subset_name = self.subset_selected
        try:
            dc = self.data_collection
            subsets = dc.subset_groups
            subset_to_update = subsets[[x.label for x in subsets].index(subset_name)]
            self.session.edit_subset_mode.edit_subset = [subset_to_update]
            self.session.edit_subset_mode._combine_data(subset_to_update.subset_state,
                                                        override_mode=ReplaceMode)
        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Failed to update Subset: {repr(err)}", color='error', sender=self))

    def _check_input(self):
        status = True
        reason = ""
        for index, sub in enumerate(self.subset_definitions):
            lo = hi = xmin = xmax = ymin = ymax = None
            inner_radius = outer_radius = None
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
                elif d_att["att"] == "outer_radius":
                    outer_radius = d_att["value"]
                elif d_att["att"] == "inner_radius":
                    inner_radius = d_att["value"]

                if lo and hi and hi <= lo:
                    status = False
                    reason = "Failed to update Subset: lower bound must be less than upper bound"
                    break
                elif xmin and xmax and ymin and ymax and (xmax - xmin <= 0 or ymax - ymin <= 0):
                    status = False
                    reason = "Failed to update Subset: width and length must be positive scalars"
                    break
                elif inner_radius and outer_radius and inner_radius >= outer_radius:
                    status = False
                    reason = "Failed to update Subset: inner radius must be less than outer radius"
                    break

        return status, reason

    def vue_recenter_subset(self, *args):
        # Composite region cannot be centered. This only works for Imviz.
        if not self.is_centerable or self.config != 'imviz':  # no-op
            raise NotImplementedError(
                f'Cannot recenter: is_centerable={self.is_centerable}, config={self.config}')

        from astropy.wcs.utils import pixel_to_pixel
        from photutils.aperture import ApertureStats
        from jdaviz.core.region_translators import regions2aperture, _get_region_from_spatial_subset

        def _do_recentering(subset, subset_state):
            try:
                reg = _get_region_from_spatial_subset(self, subset_state) # noqa
                aperture = regions2aperture(reg)
                data = self.dataset.selected_dc_item
                comp = data.get_component(data.main_components[0])
                comp_data = comp.data
                phot_aperstats = ApertureStats(comp_data, aperture, wcs=data.coords)

                # Sky region from WCS linking, need to convert centroid back to pixels.
                if hasattr(reg, "to_pixel"):
                    # Centroid was calculated in selected data.
                    # However, Subset is always defined w.r.t. its parent,
                    # so we need to convert back.
                    x, y = pixel_to_pixel(
                        data.coords,
                        subset_state.xatt.parent.coords,
                        phot_aperstats.xcentroid,
                        phot_aperstats.ycentroid)

                else:
                    x = phot_aperstats.xcentroid
                    y = phot_aperstats.ycentroid
                if not np.all(np.isfinite((x, y))):
                    raise ValueError(f'Invalid centroid ({x}, {y})')
            except Exception as err:
                self.set_center(self.get_center(subset_name=subset), subset_name=subset,
                                update=False)
                self.hub.broadcast(SnackbarMessage(
                    f"Failed to calculate centroid: {repr(err)}", color='error', sender=self))
            else:
                self.set_center((x, y), subset_name=subset, update=True)

        if not self.multiselect:
            _do_recentering(self.subset_selected, self.subset_select.selected_subset_state)
        else:
            for sub, subset_state in zip(self.subset_selected,
                                         self.subset_select.selected_subset_state):
                if (sub != self.subset_select.default_text and
                        not isinstance(subset_state, CompositeSubsetState)):
                    self.is_centerable = True
                    _do_recentering(sub, subset_state)
                elif (sub != self.subset_select.default_text and
                      isinstance(subset_state, CompositeSubsetState)):
                    self.hub.broadcast(SnackbarMessage(f"Unable to recenter "
                                                       f"composite subset {sub}",
                                                       color='error', sender=self))

    def _get_subset_state(self, subset_name=None):
        if self.multiselect and not subset_name:
            raise ValueError("Please include subset_name in when in multiselect mode")

        if subset_name is not None:
            return self.subset_select._get_subset_state(subset_name)
        # guaranteed to only return a single entry because of check above
        return self.subset_select.selected_subset_state

    def get_center(self, subset_name=None):
        """Return the center of the Subset.
        This may or may not be the centroid obtain from data.

        Parameters
        ----------
        subset_name : str
            The name of the subset that is being updated.

        Returns
        -------
        cen : number, tuple of numbers, or `None`
            The center of the Subset in ``x`` or ``(x, y)``,
            depending on the Subset type, if applicable.
            If Subset is not centerable, this returns `None`.

        """
        # Composite region cannot be centered.
        if not self.is_centerable:  # no-op
            return

        subset_state = self._get_subset_state(subset_name)
        return subset_state.center()

    def set_center(self, new_cen, subset_name=None, update=False):
        """Set the desired center for the selected Subset, if applicable.
        If Subset is not centerable, nothing is done.

        Parameters
        ----------
        new_cen : number or tuple of numbers
            The new center defined either as ``x`` or ``(x, y)``,
            depending on the Subset type.
        subset_name : str
            The name of the subset that is being updated.
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

        subset_state = self._get_subset_state(subset_name)

        if isinstance(subset_state, RoiSubsetState):
            x, y = new_cen
            # x and y are arrays so this converts them back to floats
            x = float(x)
            y = float(y)
            sbst_obj = subset_state.roi
            if isinstance(sbst_obj, (CircularROI, CircularAnnulusROI, EllipticalROI)):
                sbst_obj.move_to(x, y)
            elif isinstance(sbst_obj, RectangularROI):
                sbst_obj.move_to(x, y)
            else:  # pragma: no cover
                raise NotImplementedError(f'Recentering of {sbst_obj.__class__} is not supported')

        elif isinstance(subset_state, RangeSubsetState):
            subset_state.move_to(new_cen)

        else:  # pragma: no cover
            raise NotImplementedError(
                f'Getting center of {subset_state.__class__} is not supported')

        if update:
            self._push_update_to_ui(subset_name=subset_name)
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
