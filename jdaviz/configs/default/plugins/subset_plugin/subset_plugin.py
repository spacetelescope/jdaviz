import os

import numpy as np

from astropy.time import Time
import astropy.units as u
from glue.core.message import EditSubsetMessage, SubsetUpdateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode, NewMode)
from glue.core.roi import CircularROI, CircularAnnulusROI, EllipticalROI, RectangularROI
from glue.core.subset import (RoiSubsetState, RangeSubsetState, CompositeSubsetState,
                              MaskSubsetState)
from glue.icons import icon_path
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Any, List, Unicode, Bool, observe

from specutils import SpectralRegion
from photutils.aperture import (CircularAperture, SkyCircularAperture,
                                EllipticalAperture, SkyEllipticalAperture,
                                RectangularAperture, SkyRectangularAperture,
                                CircularAnnulus, SkyCircularAnnulus)
from regions import (Regions, CirclePixelRegion, CircleSkyRegion,
                     EllipsePixelRegion, EllipseSkyRegion,
                     RectanglePixelRegion, RectangleSkyRegion,
                     CircleAnnulusPixelRegion, CircleAnnulusSkyRegion)

from jdaviz.core.region_translators import regions2roi, aperture2regions
from jdaviz.core.events import SnackbarMessage, GlobalDisplayUnitChanged, LinkUpdatedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        SubsetSelect, SelectPluginComponent)
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.helpers import _next_subset_num
from jdaviz.utils import MultiMaskSubsetState, data_has_valid_wcs

from jdaviz.configs.default.plugins.subset_plugin import utils


__all__ = ['SubsetPlugin']

SUBSET_MODES = {
    'new': NewMode,
    'replace': ReplaceMode,
    'OrState': OrMode,
    'AndState': AndMode,
    'XorState': XorMode,
    'AndNotState': AndNotMode,
    'RangeSubsetState': RangeSubsetState,
    'RoiSubsetState': RoiSubsetState
}
SUBSET_MODES_PRETTY = {
    'new': NewMode,
    'replace': ReplaceMode,
    'or': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'andnot': AndNotMode,
}
SUBSET_TO_PRETTY = {v: k for k, v in SUBSET_MODES_PRETTY.items()}
COMBO_OPTIONS = list(SUBSET_MODES_PRETTY.keys())


@tray_registry('g-subset-plugin', label="Subset Tools")
class SubsetPlugin(PluginTemplateMixin, DatasetSelectMixin):
    """
    See the :ref:`Subset Tools <imviz-subset-plugin>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """
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

    combination_items = List([]).tag(sync=True)
    combination_selected = Any().tag(sync=True)

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
        self.session.hub.subscribe(self, LinkUpdatedMessage,
                                   handler=self._on_link_update)

        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          multiselect='multiselect',
                                          default_text="Create New")
        self.subset_states = []
        self.spectral_display_unit = None

        align_by = getattr(self.app, '_align_by', None)
        self.display_sky_coordinates = (align_by == 'wcs' and not self.multiselect)

        self.combination_mode = SelectPluginComponent(self,
                                                      items='combination_items',
                                                      selected='combination_selected',
                                                      manual_options=COMBO_OPTIONS)

    @property
    def user_api(self):
        expose = []
        return PluginUserApi(self, expose)

    def _on_link_update(self, *args):
        """When linking is changed pixels<>wcs, change display units of the
        subset plugin from pixel (for pixel linking) to sky (for WCS linking).
        If there is an active selection in the subset plugin, push this change
        to the UI upon link change by calling _get_subset_definition, which
        will re-determine how to display subset information."""

        align_by = getattr(self.app, '_align_by', None)
        self.display_sky_coordinates = (align_by == 'wcs')

        if self.subset_selected != self.subset_select.default_text:
            self._get_subset_definition(*args)

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
        self._update_combination_mode()

    def _on_subset_update(self, *args):
        self._sync_selected_from_state(*args)
        if 'Create New' in self.subset_selected:
            return
        subsets_avail = [sg.label for sg in self.app.data_collection.subset_groups]
        if self.subset_selected not in subsets_avail:
            # subset selection should re-default after processing the deleted subset,
            # for now we can safely ignore
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

        include_sky_region = bool(self.display_sky_coordinates)
        subset_information = self.app.get_subsets(self.subset_selected,
                                                  simplify_spectral=False,
                                                  use_display_units=True,
                                                  include_sky_region=include_sky_region)

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

                sky_region = spec['sky_region']
                if self.display_sky_coordinates and (sky_region is not None):
                    subset_definition += utils._sky_region_to_subset_def(sky_region)

                else:
                    if isinstance(subset_state.roi, CircularROI):
                        x, y = subset_state.roi.center()
                        r = subset_state.roi.radius
                        subset_definition += [
                            {"name": "X Center (pixels)", "att": "xc",
                             "value": x, "orig": x},
                            {"name": "Y Center (pixels)", "att": "yc",
                             "value": y, "orig": y},
                            {"name": "Radius (pixels)", "att": "radius",
                             "value": r, "orig": r}]

                    elif isinstance(subset_state.roi, RectangularROI):
                        for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
                            real_att = att.lower()
                            val = getattr(subset_state.roi, real_att)
                            subset_definition.append(
                                {"name": att + " (pixels)", "att": real_att,
                                 "value": val, "orig": val})

                        theta = np.around(np.degrees(subset_state.roi.theta),
                                          decimals=_around_decimals)
                        subset_definition.append({"name": "Angle", "att": "theta",
                                                  "value": theta, "orig": theta})

                    elif isinstance(subset_state.roi, EllipticalROI):
                        xc, yc = subset_state.roi.center()
                        rx = subset_state.roi.radius_x
                        ry = subset_state.roi.radius_y
                        theta = np.around(np.degrees(subset_state.roi.theta),
                                          decimals=_around_decimals)

                        subset_definition += [
                            {"name": "X Center (pixels)", "att": "xc",
                             "value": xc, "orig": xc},
                            {"name": "Y Center (pixels)", "att": "yc",
                             "value": yc, "orig": yc},
                            {"name": "X Radius (pixels)", "att": "radius_x",
                             "value": rx, "orig": rx},
                            {"name": "Y Radius (pixels)", "att": "radius_y",
                             "value": ry, "orig": ry},
                            {"name": "Angle", "att": "theta",
                             "value": theta, "orig": theta}]

                    elif isinstance(subset_state.roi, CircularAnnulusROI):
                        xc, yc = subset_state.roi.center()
                        inner_r = subset_state.roi.inner_radius
                        outer_r = subset_state.roi.outer_radius
                        subset_definition += [{"name": "X Center (pixels)",
                                               "att": "xc", "value": xc, "orig": xc},
                                              {"name": "Y Center (pixels)",
                                               "att": "yc", "value": yc, "orig": yc},
                                              {"name": "Inner Radius (pixels)",
                                               "att": "inner_radius",
                                               "value": inner_r, "orig": inner_r},
                                              {"name": "Outer Radius (pixels)",
                                               "att": "outer_radius",
                                               "value": outer_r, "orig": outer_r}]

                    else:  # pragma: no cover
                        raise NotImplementedError(f"Unable to translate {subset_state.roi.__class__.__name__}")  # noqa: E501

                subset_type = subset_state.roi.__class__.__name__

            elif isinstance(subset_state, RangeSubsetState):
                region = spec['region']
                if isinstance(region, Time):
                    lo = region.min()
                    hi = region.max()
                    subset_definition = [{"name": "Lower bound", "att": "lo",
                                          "value": lo.value, "orig": lo.value},
                                         {"name": "Upper bound", "att": "hi",
                                          "value": hi.value, "orig": hi.value}]
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
        # Check if the subset has more than one subregion, is a range subset
        # type, and uses one of the states that can be simplified. Mask subset
        # types cannot be simplified so subsets contained that are skipped.
        if 'Mask' in self.subset_types:
            self.can_simplify = False
        elif ((len(self.subset_states) > 1) and isinstance(self.subset_states[0], RangeSubsetState)
              and ((len(simplifiable_states - set(self.glue_state_types)) < 3)
                   or self.app.is_there_overlap_spectral_subset(self.subset_selected))):
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

            # we need to push updates to subset in pixels. to do this when wcs
            # linked, convert the updated subset parameters from sky to pix
            wcs = None

            if self.display_sky_coordinates:
                wcs = self.app._get_wcs_from_subset(sub_states)

                if wcs is not None:
                    # convert newly entered sky coords to pixel
                    updated_skyreg = utils._subset_def_to_region(self.subset_types[index], sub)  # noqa
                    updated_pixreg_attrs = utils._get_pixregion_params_in_dict(updated_skyreg.to_pixel(wcs))  # noqa
                    # convert previous entered sky coords to pixel
                    orig_skyreg = utils._subset_def_to_region(self.subset_types[index], sub, val='orig')  # noqa
                    orig_pixreg_attrs = utils._get_pixregion_params_in_dict(orig_skyreg.to_pixel(wcs))  # noqa

            for d_att in sub:
                if d_att["att"] == 'parent':  # Read-only
                    continue
                if self.display_sky_coordinates and (wcs is not None):
                    d_att["value"] = updated_pixreg_attrs[d_att["att"]]
                    d_att["orig"] = orig_pixreg_attrs[d_att["att"]]

                if (d_att["att"] == 'theta') and (self.display_sky_coordinates is False):
                    # Humans use degrees but glue uses radians
                    # We've already enforced this in wcs linking in _get_pixregion_params_in_dict
                    d_val = np.radians(d_att["value"])
                else:
                    d_val = float(d_att["value"])

                # Convert from display unit to original unit if necessary
                if self.subset_types[index] == "Range":
                    if self.spectral_display_unit is not None:
                        x_att = sub_states.att
                        # since this is a spectrum range subset, we can get the native units
                        # from the current reference data in the spectrum viewer
                        sv = self.spectrum_viewer
                        base_units = sv.state.reference_data.get_component(x_att).units
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
                reg = _get_region_from_spatial_subset(self, subset_state)
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

    def import_region(self, region, combination_mode=None, max_num_regions=None,
                      refdata_label=None, return_bad_regions=False, **kwargs):
        """
        Method for creating subsets from regions or region files.

        Parameters
        ----------
        region : region, list of region objects, or str
            A region object can be one of the following:

            * Astropy ``regions`` object
            * ``photutils`` apertures (limited support until ``photutils``
              fully supports ``regions``)
            * specutils ``SpectralRegion`` object

            A string which represents a ``regions`` or ``SpectralRegion`` file.
            If given as a list, it can only contain spectral or non-spectral regions, not both.

        combination_mode : list, str, or `None`
            The way that regions are created or combined. If a list, then it must be the
            same length as regions. If `None`, then it will follow the default glue
            functionality for subset creation.

        max_num_regions : int or `None`
            Maximum number of regions to load, starting from top of the list.
            Default is to load everything.  If you are providing a large file/list
            input for ``region``, it is recommended

        refdata_label : str or `None`
            **This is only applicable to non-spectral regions.**
            Label of data to use for sky-to-pixel conversion for a region, or
            mask creation. Data must already be loaded into Jdaviz.
            If `None`, defaults to the reference data in the default viewer.
            Choice of this data is particularly important when sky
            region is involved.

        return_bad_regions : bool
            If `True`, return the regions that failed to load (see ``bad_regions``);
            This is useful for debugging. If `False`, do not return anything (`None`).

        Returns
        -------
        bad_regions : list of (obj, str) or `None`
            If requested (see ``return_bad_regions`` option), return a
            list of ``(region, reason)`` tuples for region objects that failed to load.
            If all the regions loaded successfully, this list will be empty.
            If not requested, return `None`.

        """
        if isinstance(region, str):
            if os.path.exists(region):
                from regions import Regions
                region_format = kwargs.pop('region_format', None)
                try:
                    raw_regs = Regions.read(region, format=region_format)
                except Exception:  # nosec
                    raw_regs = SpectralRegion.read(region)

                return self._load_regions(raw_regs, combination_mode, max_num_regions,
                                          refdata_label, return_bad_regions, **kwargs)
        else:
            return self._load_regions(region, combination_mode, max_num_regions, refdata_label,
                                      return_bad_regions, **kwargs)

    def _load_regions(self, regions, combination_mode=None, max_num_regions=None,
                      refdata_label=None, return_bad_regions=False, **kwargs):
        """Load given region(s) into the viewer.
        WCS-to-pixel translation and mask creation, if needed, is relative
        to the image defined by ``refdata_label``. Meanwhile, the rest of
        the Subset operations are based on reference image as defined by Glue.

        .. note:: Loading too many regions will affect performance.

        A valid region can be loaded into one of the following categories:

        * An interactive Subset, as if it was drawn by hand. This is
          always done for supported shapes. Its label will be
          ``'Subset N'``, where ``N`` is an integer.
        * A masked Subset that will display on the image but cannot be
          modified once loaded. This is done if the shape cannot be
          made interactive. Its label will be ``'MaskedSubset N'``,
          where ``N`` is an integer.

        Parameters
        ----------
        regions : list of obj
            A list of region objects. A region object can be one of the following:

            * Astropy ``regions`` object
            * ``photutils`` apertures (limited support until ``photutils``
              fully supports ``regions``)
            * specutils ``SpectralRegion`` object

        combination_mode : list, str, or `None`
            The way that regions are created or combined. If a list, then it must be the
            same length as regions. Each element describes how the corresponding region
            in regions will be applied. If `None`, then it will follow the default glue
            functionality for subset creation. Options are ['new', 'replace', 'or', 'and',
            'xor', 'andnot']

        max_num_regions : int or `None`
            Maximum number of regions to load, starting from top of the list.
            Default is to load everything.

        refdata_label : str or `None`
            Label of data to use for sky-to-pixel conversion for a region, or
            mask creation. Data must already be loaded into Jdaviz.
            If `None`, defaults to the reference data in the default viewer.
            Choice of this data is particularly important when sky
            region is involved.

        return_bad_regions : bool
            If `True`, return the regions that failed to load (see ``bad_regions``);
            This is useful for debugging. If `False`, do not return anything (`None`).

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            **This is ignored if the region can be made interactive.**

        Returns
        -------
        bad_regions : list of (obj, str) or `None`
            If requested (see ``return_bad_regions`` option), return a
            list of ``(region, reason)`` tuples for region objects that failed to load.
            If all the regions loaded successfully, this list will be empty.
            If not requested, return `None`.

        """
        if len(self.app.data_collection) == 0:
            raise ValueError('Cannot load regions without data.')

        if not isinstance(regions, (list, tuple, Regions, SpectralRegion)):
            regions = [regions]

        n_loaded = 0
        bad_regions = []

        # To keep track of masked subsets.
        msg_prefix = 'MaskedSubset'
        msg_count = _next_subset_num(msg_prefix, self.app.data_collection.subset_groups)

        viewer_parameter = kwargs.pop('viewer', None)
        viewer_name = viewer_parameter or list(self.app._jdaviz_helper.viewers.keys())[0]
        viewer = self.app.get_viewer(viewer_name)
        # Subset is global but reference data is viewer-dependent.
        if refdata_label is None:
            data = viewer.state.reference_data
        else:
            data = self.app.data_collection[refdata_label]

        has_wcs = data_has_valid_wcs(data, ndim=2)

        combo_mode_is_list = isinstance(combination_mode, list)
        if combo_mode_is_list and len(combination_mode) != (len(regions)):
            raise ValueError("list of mode must be size of regions")
        elif combo_mode_is_list:
            for mode in combination_mode:
                if mode not in COMBO_OPTIONS:
                    raise ValueError(f"{mode} not one of {COMBO_OPTIONS}")

        for index, region in enumerate(regions):
            # Set combination mode for how region will be applied to current subset
            # or created as a new subset
            if combo_mode_is_list:
                combo_mode = combination_mode[index]
            else:
                combo_mode = combination_mode

            if combo_mode == 'new':
                # Remove selection of subset so that new one will be created
                self.app.session.edit_subset_mode.edit_subset = None  # No overwrite next iteration
                self.app.session.edit_subset_mode.mode = SUBSET_MODES_PRETTY['new']
            elif combo_mode:
                self.combination_mode.selected = combo_mode

            if (isinstance(region, (SkyCircularAperture, SkyEllipticalAperture,
                                    SkyRectangularAperture, SkyCircularAnnulus,
                                    CircleSkyRegion, EllipseSkyRegion,
                                    RectangleSkyRegion, CircleAnnulusSkyRegion))
                    and not has_wcs):
                bad_regions.append((region, 'Sky region provided but data has no valid WCS'))
                continue

            if (isinstance(region, (CircularAperture, EllipticalAperture,
                                    RectangularAperture, CircularAnnulus,
                                    CirclePixelRegion, EllipsePixelRegion,
                                    RectanglePixelRegion, CircleAnnulusPixelRegion))
                    and (hasattr(self.app, '_link_type') and self.app._link_type == "wcs")):
                bad_regions.append((region, 'Pixel region provided by data is linked by WCS'))
                continue

            # photutils: Convert to region shape first
            if isinstance(region, (CircularAperture, SkyCircularAperture,
                                   EllipticalAperture, SkyEllipticalAperture,
                                   RectangularAperture, SkyRectangularAperture,
                                   CircularAnnulus, SkyCircularAnnulus)):
                region = aperture2regions(region)

            # region: Convert to ROI.
            # NOTE: Out-of-bounds ROI will succeed; this is native glue behavior.
            if isinstance(region, (CirclePixelRegion, CircleSkyRegion,
                                   EllipsePixelRegion, EllipseSkyRegion,
                                   RectanglePixelRegion, RectangleSkyRegion,
                                   CircleAnnulusPixelRegion, CircleAnnulusSkyRegion)):
                state = regions2roi(region, wcs=data.coords)
                viewer.apply_roi(state)

            elif isinstance(region, (CircularROI, CircularAnnulusROI,
                                     EllipticalROI, RectangularROI)):
                viewer.apply_roi(region)

            elif isinstance(region, SpectralRegion):
                # Use viewer_name if provided in kwarg, otherwise use
                # default spectrum viewer name
                viewer_name = (viewer_parameter or
                               self.app._jdaviz_helper._default_spectrum_viewer_reference_name)
                range_viewer = self.app.get_viewer(viewer_name)

                s = RangeSubsetState(lo=region.lower.value, hi=region.upper.value,
                                     att=range_viewer.state.x_att)
                range_viewer.apply_subset_state(s)

            # Last resort: Masked Subset that is static (if data is not a cube)
            elif data.ndim == 2:
                im = None
                if hasattr(region, 'to_pixel'):  # Sky region: Convert to pixel region
                    if not has_wcs:
                        bad_region.append((region, 'Sky region provided but data has no valid WCS'))  # noqa
                        continue
                    region = region.to_pixel(data.coords)

                if hasattr(region, 'to_mask'):
                    try:
                        mask = region.to_mask(**kwargs)
                        im = mask.to_image(data.shape)  # Can be None
                    except Exception as e:  # pragma: no cover
                        bad_regions.append((region, f'Failed to load: {repr(e)}'))
                        continue

                # Boolean mask as input is supported but not advertised.
                elif (isinstance(region, np.ndarray) and region.shape == data.shape
                      and region.dtype == np.bool_):
                    im = region

                if im is None:
                    bad_regions.append((region, 'Mask creation failed'))
                    continue

                # NOTE: Region creation info is thus lost.
                try:
                    subset_label = f'{msg_prefix} {msg_count}'
                    state = MaskSubsetState(im, data.pixel_component_ids)
                    self.app.data_collection.new_subset_group(subset_label, state)
                    msg_count += 1
                except Exception as e:  # pragma: no cover
                    bad_regions.append((region, f'Failed to load: {repr(e)}'))
                    continue
            else:
                bad_regions.append((region, 'Mask creation failed'))
                continue
            n_loaded += 1
            if max_num_regions is not None and n_loaded >= max_num_regions:
                break

        n_reg_in = len(regions)
        n_reg_bad = len(bad_regions)
        if n_loaded == 0:
            snack_color = "error"
        elif n_reg_bad > 0:
            snack_color = "warning"
        else:
            snack_color = "success"
        self.app.hub.broadcast(SnackbarMessage(
            f"Loaded {n_loaded}/{n_reg_in} regions, max_num_regions={max_num_regions}, "
            f"bad={n_reg_bad}", color=snack_color, timeout=8000, sender=self.app))

        if return_bad_regions:
            return bad_regions

    @observe('combination_selected')
    def _combination_selected_updated(self, change):
        self.app.session.edit_subset_mode.mode = SUBSET_MODES_PRETTY[change['new']]

    def _update_combination_mode(self):
        if self.app.session.edit_subset_mode.mode in SUBSET_TO_PRETTY.keys():
            self.combination_mode.selected = SUBSET_TO_PRETTY[
                self.app.session.edit_subset_mode.mode]
