import numpy as np
from astropy import units as u
from traitlets import List, Unicode, observe, Bool

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, UnitSelectPluginComponent,
                                        SelectPluginComponent, PluginUserApi)
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list,
                                    create_sb_equivalencies_list,
                                    check_if_unit_is_per_solid_angle,
                                    units_to_strings)

__all__ = ['UnitConversion']


def _valid_glue_display_unit(unit_str, sv, axis='x'):
    # need to make sure the unit string is formatted according to the list of valid choices
    # that glue will accept (may not be the same as the defaults of the installed version of
    # astropy)
    if not unit_str:
        return unit_str
    unit_u = u.Unit(unit_str)
    choices_str = getattr(sv.state.__class__, f'{axis}_display_unit').get_choices(sv.state)
    choices_str = [choice for choice in choices_str if choice is not None]
    choices_u = [u.Unit(choice) for choice in choices_str]
    if unit_u not in choices_u:
        raise ValueError(f"{unit_str} could not find match in valid {axis} display units {choices_str}")  # noqa
    ind = choices_u.index(unit_u)
    return choices_str[ind]


@tray_registry('g-unit-conversion', label="Unit Conversion",
               viewer_requirements='spectrum')
class UnitConversion(PluginTemplateMixin):
    """
    The Unit Conversion plugin handles global app-wide unit-conversion.
    See the :ref:`Unit Conversion Plugin Documentation <unit-conversion>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``spectral_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global unit to use for all spectral axes.
    * ``flux_or_sb`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Y-axis physical type selection. Currently only accessible in Cubeviz.
    * ``flux_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global flux unit to use for y-axis.
    * ``sb_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global surface brightness unit to use for y-axis.
    """
    template_file = __file__, "unit_conversion.vue"

    spectral_unit_items = List().tag(sync=True)
    spectral_unit_selected = Unicode().tag(sync=True)

    flux_unit_items = List().tag(sync=True)
    flux_unit_selected = Unicode().tag(sync=True)

    sb_unit_items = List().tag(sync=True)
    sb_unit_selected = Unicode().tag(sync=True)

    show_translator = Bool(False).tag(sync=True)
    flux_or_sb_items = List().tag(sync=True)
    flux_or_sb_selected = Unicode().tag(sync=True)

    can_translate = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config not in ['specviz', 'cubeviz']:
            # TODO [specviz2d, mosviz] x_display_unit is not implemented in glue for image viewer
            # used by spectrum-2d-viewer
            # TODO [mosviz]: add to yaml file
            # TODO [cubeviz, slice]: slice indicator broken after changing spectral_unit
            # TODO: support for multiple viewers and handling of mixed state from glue (or does
            # this force all to sync?)
            self.disabled_msg = f'This plugin is temporarily disabled in {self.config}. Effort to improve it is being tracked at GitHub Issue 1972.'  # noqa

        # TODO [markers]: existing markers need converting
        self.spectrum_viewer.state.add_callback('x_display_unit',
                                                self._on_glue_x_display_unit_changed)

        self.spectrum_viewer.state.add_callback('y_display_unit',
                                                self._on_glue_y_display_unit_changed)

        self.spectral_unit = UnitSelectPluginComponent(self,
                                                       items='spectral_unit_items',
                                                       selected='spectral_unit_selected')

        self.flux_or_sb = SelectPluginComponent(self,
                                                items='flux_or_sb_items',
                                                selected='flux_or_sb_selected',
                                                manual_options=['Surface Brightness', 'Flux'])

        self.flux_unit = UnitSelectPluginComponent(self,
                                                   items='flux_unit_items',
                                                   selected='flux_unit_selected')

        self.sb_unit = UnitSelectPluginComponent(self,
                                                 items='sb_unit_items',
                                                 selected='sb_unit_selected')

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('spectral_unit', 'flux_or_sb', 'flux_unit', 'sb_unit'))

    def _on_glue_x_display_unit_changed(self, x_unit):
        if x_unit is None:
            return
        self.spectrum_viewer.set_plot_axes()
        if x_unit != self.spectral_unit.selected:
            x_unit = _valid_glue_display_unit(x_unit, self.spectrum_viewer, 'x')
            x_u = u.Unit(x_unit)
            choices = create_spectral_equivalencies_list(x_u)
            # ensure that original entry is in the list of choices
            if not np.any([x_u == u.Unit(choice) for choice in choices]):
                choices = [x_unit] + choices
            self.spectral_unit.choices = choices
            # in addition to the jdaviz options, allow the user to set any glue-valid unit
            # which would then be appended on to the list of choices going forward
            self.spectral_unit._addl_unit_strings = self.spectrum_viewer.state.__class__.x_display_unit.get_choices(self.spectrum_viewer.state)  # noqa
            self.spectral_unit.selected = x_unit
            if not len(self.flux_unit.choices) or not len(self.sb_unit.choices):
                # in case flux_unit was triggered first (but could not be set because there
                # as no spectral_unit to determine valid equivalencies)
                self._on_glue_y_display_unit_changed(self.spectrum_viewer.state.y_display_unit)

    def _on_glue_y_display_unit_changed(self, y_unit):
        if y_unit is None:
            return
        if self.spectral_unit.selected == "":
            # no spectral unit set yet, cannot determine equivalencies
            # setting the spectral unit will check len(flux_or_sb_unit.choices)
            # and call this manually in the case that that is triggered second.
            return
        self.spectrum_viewer.set_plot_axes()

        flux_or_sb = ''
        if check_if_unit_is_per_solid_angle(y_unit):
            flux_or_sb = 'Surface Brightness'
        else:
            flux_or_sb = 'Flux'

        x_u = u.Unit(self.spectral_unit.selected)
        y_unit = _valid_glue_display_unit(y_unit, self.spectrum_viewer, 'y')
        y_u = u.Unit(y_unit)

        if flux_or_sb == 'Flux' and y_unit != self.flux_unit.selected:
            flux_choices = create_flux_equivalencies_list(y_u, x_u)
            sb_choices = create_sb_equivalencies_list(y_u * u.sr, x_u)

            # ensure that original entry is in the list of choices
            if not np.any([y_u == u.Unit(choice) for choice in flux_choices]):
                flux_choices = [y_unit] + flux_choices

            self.flux_unit.choices = flux_choices
            self.sb_unit.choices = sb_choices
            self.flux_unit.selected = y_unit

        elif flux_or_sb == 'Surface Brightness' and y_unit != self.sb_unit.selected:
            flux_choices = create_flux_equivalencies_list(y_u / u.sr, x_u)
            sb_choices = create_sb_equivalencies_list(y_u, x_u)

            # ensure that original entry is in the list of choices
            if not np.any([y_u == u.Unit(choice) for choice in sb_choices]):
                sb_choices = [y_unit] + sb_choices

            self.flux_unit.choices = flux_choices
            self.sb_unit.choices = sb_choices
            self.sb_unit.selected = y_unit

    def translate_units(self, flux_or_sb_selected):
        spec_units = u.Unit(self.spectrum_viewer.state.y_display_unit)
        # Surface Brightness -> Flux
        if check_if_unit_is_per_solid_angle(spec_units) and flux_or_sb_selected == 'Flux':
            spec_units *= u.sr
            # update display units
            self.spectrum_viewer.state.y_display_unit = str(spec_units)
            self.flux_or_sb.selected = 'Flux'

        # Flux -> Surface Brightness
        elif (not check_if_unit_is_per_solid_angle(spec_units)
              and flux_or_sb_selected == 'Surface Brightness'):
            spec_units /= u.sr
            # update display units
            self.spectrum_viewer.state.y_display_unit = str(spec_units)
            self.flux_or_sb.selected = 'Surface Brightness'

        self.spectrum_viewer.reset_limits()

    @observe('spectral_unit_selected')
    def _on_spectral_unit_changed(self, *args):
        xunit = _valid_glue_display_unit(self.spectral_unit.selected, self.spectrum_viewer, 'x')
        if self.spectrum_viewer.state.x_display_unit != xunit:
            self.spectrum_viewer.state.x_display_unit = xunit
            self.hub.broadcast(GlobalDisplayUnitChanged('spectral',
                               self.spectral_unit.selected,
                               sender=self))

    @observe('flux_unit_selected', 'sb_unit_selected')
    def _on_flux_unit_changed(self, *args):
        flux_or_sb = None
        current_y = self.spectrum_viewer.state.y_display_unit

        for arg in args:
            # determine if flux or surface brightness unit was changed  by user
            if arg['name'] == 'flux_unit_selected':
                flux_or_sb = self.flux_unit.selected
                # update flux or surface brightness dropdown if necessary
                if check_if_unit_is_per_solid_angle(current_y):
                    self.flux_or_sb.selected = 'Flux'

                untranslatable_units = [
                    u.erg / (u.s * u.cm**2),
                    u.erg / (u.s * u.cm**2 * u.Angstrom),
                    u.erg / (u.s * u.cm**2 * u.Hz),
                    u.ph / (u.Angstrom * u.s * u.cm**2),
                    u.ph / (u.s * u.cm**2 * u.Hz),
                    u.ST, u.bol
                ]
                # disable translator is flux unit is untranslatable
                # still can select surface brightness units, just disables
                # flux -> surface brightnes of particular unit selected.
                if flux_or_sb in untranslatable_units:
                    self.can_translate = False
                else:
                    self.can_translate = True

            elif arg['name'] == 'sb_unit_selected':
                flux_or_sb = self.sb_unit.selected
                self.can_translate = True
                # update flux or surface brightness dropdown if necessary
                if not check_if_unit_is_per_solid_angle(current_y):
                    self.flux_or_sb.selected = 'Surface Brightness'

        yunit = _valid_glue_display_unit(flux_or_sb, self.spectrum_viewer, 'y')

        if self.spectrum_viewer.state.y_display_unit != yunit:
            self.spectrum_viewer.state.y_display_unit = yunit
            self.hub.broadcast(GlobalDisplayUnitChanged('flux',
                                                        flux_or_sb,
                                                        sender=self))
            self.spectrum_viewer.reset_limits()

    # Ensure first dropdown selection for Flux/Surface Brightness
    # is in accordance with the data collection item's units.
    @observe('show_translator')
    def _set_flux_or_sb(self, *args):
        if (self.spectrum_viewer and hasattr(self.spectrum_viewer.state, 'y_display_unit')
           and self.spectrum_viewer.state.y_display_unit is not None):
            self.flux_or_sb_selected = 'Flux'

    @observe('flux_or_sb_selected', 'flux_unit_selected', 'sb_unit_selected')
    def _translate(self, *args):
        # currently unsupported, can be supported with a scale factor
        if self.app.config == 'specviz':
            return
        # The translator dropdown hasn't been loaded yet so don't try translating
        if not self.show_translator:
            return

        flux_or_sb = None

        if args:
            # need to check current y_unit to see if we need to translate
            y_unit = self.spectrum_viewer.state.y_display_unit
            for arg in args:
                if arg['name'] == 'flux_unit_selected':
                    # don't translate if self.flux_or_sb == Flux
                    if not check_if_unit_is_per_solid_angle(y_unit):
                        return
                    flux_or_sb = 'Flux'
                elif arg['name'] == 'sb_unit_selected':
                    # don't translate if self.flux_or_sb == Surface Brightness
                    if check_if_unit_is_per_solid_angle(y_unit):
                        return
                    flux_or_sb = 'Surface Brightness'
                elif arg['name'] == 'flux_or_sb_selected':
                    flux_or_sb = self.flux_or_sb_selected
                else:
                    return

        # we want to raise an error if a user tries to translate with an
        # untranslated Flux unit using the API
        untranslatable_units = [
                    u.erg / (u.s * u.cm**2),
                    u.erg / (u.s * u.cm**2 * u.Angstrom),
                    u.erg / (u.s * u.cm**2 * u.Hz),
                    u.ph / (u.Angstrom * u.s * u.cm**2),
                    u.ph / (u.s * u.cm**2 * u.Hz),
                    u.ST, u.bol
                ]
        untranslatable_units = units_to_strings(untranslatable_units)

        if self.flux_unit.selected in untranslatable_units and flux_or_sb == 'Surface Brightness':
            raise ValueError(
                f"Selected flux unit is not translatable. Please choose a flux unit "
                f"that is not in the following list: {untranslatable_units}."
            )

        self.translate_units(flux_or_sb)
