import numpy as np
from astropy import units as u
from traitlets import List, Unicode, observe, Bool

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, UnitSelectPluginComponent,
                                        SelectPluginComponent, PluginUserApi)
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list,
                                    check_if_unit_is_per_solid_angle,
                                    units_to_strings,
                                    create_angle_equivalencies_list)

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
      Select the y-axis physical type for the spectrum-viewer.
    * ``flux_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global display unit for flux axis.
    * ``angle_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Solid angle unit.
    """
    template_file = __file__, "unit_conversion.vue"

    spectral_unit_items = List().tag(sync=True)
    spectral_unit_selected = Unicode().tag(sync=True)

    flux_unit_items = List().tag(sync=True)
    flux_unit_selected = Unicode().tag(sync=True)

    sb_unit_selected = Unicode().tag(sync=True)

    angle_unit_items = List().tag(sync=True)
    angle_unit_selected = Unicode().tag(sync=True)

    flux_or_sb_items = List().tag(sync=True)
    flux_or_sb_selected = Unicode().tag(sync=True)

    can_translate = Bool(True).tag(sync=True)
    # This is used a warning message if False. This can be changed from
    # bool to unicode when we eventually handle inputing this value if it
    # doesn't exist in the FITS header
    pixar_sr_exists = Bool(True).tag(sync=True)

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

        self.angle_unit = UnitSelectPluginComponent(self,
                                                    items='angle_unit_items',
                                                    selected='angle_unit_selected')

    @property
    def user_api(self):
        if self.app.config == 'cubeviz':
            expose = ('spectral_unit', 'flux_or_sb', 'flux_unit', 'angle_unit')
        else:
            expose = ('spectral_unit', 'flux_unit', 'angle_unit')
        return PluginUserApi(self, expose=expose)

    def _on_glue_x_display_unit_changed(self, x_unit_str):
        if x_unit_str is None:
            return
        self.spectrum_viewer.set_plot_axes()
        if x_unit_str != self.spectral_unit.selected:
            x_unit_str = _valid_glue_display_unit(x_unit_str, self.spectrum_viewer, 'x')
            x_unit = u.Unit(x_unit_str)
            choices = create_spectral_equivalencies_list(x_unit)
            # ensure that original entry is in the list of choices
            if not np.any([x_unit == u.Unit(choice) for choice in choices]):
                choices = [x_unit_str] + choices
            self.spectral_unit.choices = choices
            # in addition to the jdaviz options, allow the user to set any glue-valid unit
            # which would then be appended on to the list of choices going forward
            self.spectral_unit._addl_unit_strings = self.spectrum_viewer.state.__class__.x_display_unit.get_choices(self.spectrum_viewer.state)  # noqa
            self.spectral_unit.selected = x_unit_str
            if not len(self.flux_unit.choices) or not len(self.angle_unit.choices):
                # in case flux_unit was triggered first (but could not be set because there
                # as no spectral_unit to determine valid equivalencies)
                self._on_glue_y_display_unit_changed(self.spectrum_viewer.state.y_display_unit)

    def _on_glue_y_display_unit_changed(self, y_unit_str):
        if y_unit_str is None:
            return
        if self.spectral_unit.selected == "":
            # no spectral unit set yet, cannot determine equivalencies
            # setting the spectral unit will check len(flux_or_sb_unit.choices)
            # and call this manually in the case that that is triggered second.
            return
        self.spectrum_viewer.set_plot_axes()

        x_unit = u.Unit(self.spectral_unit.selected)
        y_unit_str = _valid_glue_display_unit(y_unit_str, self.spectrum_viewer, 'y')
        y_unit = u.Unit(y_unit_str)

        if not check_if_unit_is_per_solid_angle(y_unit_str) and y_unit_str != self.flux_unit.selected:  # noqa
            flux_choices = create_flux_equivalencies_list(y_unit, x_unit)
            # ensure that original entry is in the list of choices
            if not np.any([y_unit == u.Unit(choice) for choice in flux_choices]):
                flux_choices = [y_unit_str] + flux_choices

            self.flux_unit.choices = flux_choices
            self.flux_unit.selected = y_unit_str

        # if the y-axis is set to surface brightness,
        # untranslatable units need to be removed from the flux choices
        if check_if_unit_is_per_solid_angle(y_unit_str):
            updated_flux_choices = list(set(create_flux_equivalencies_list(y_unit * u.sr, x_unit))
                                        - set(units_to_strings(self._untranslatable_units)))
            self.flux_unit.choices = updated_flux_choices

        # sets the angle unit drop down and the surface brightness read-only text
        if self.app.data_collection[0]:
            dc_unit = self.app.data_collection[0].get_component("flux").units
            self.angle_unit.choices = create_angle_equivalencies_list(dc_unit)
            self.angle_unit.selected = self.angle_unit.choices[0]
            self.sb_unit_selected = self._append_angle_correctly(
                self.flux_unit.selected,
                self.angle_unit.selected
            )
            self.hub.broadcast(GlobalDisplayUnitChanged('sb',
                                                        self.sb_unit_selected,
                                                        sender=self))

            if not self.flux_unit.selected:
                y_display_unit = self.spectrum_viewer.state.y_display_unit
                self.flux_unit.selected = (str(u.Unit(y_display_unit * u.sr)))

    @observe('spectral_unit_selected')
    def _on_spectral_unit_changed(self, *args):
        xunit = _valid_glue_display_unit(self.spectral_unit.selected, self.spectrum_viewer, 'x')
        if self.spectrum_viewer.state.x_display_unit != xunit:
            self.spectrum_viewer.state.x_display_unit = xunit
            self.hub.broadcast(GlobalDisplayUnitChanged('spectral',
                               self.spectral_unit.selected,
                               sender=self))

    @observe('flux_or_sb_selected')
    def _on_flux_or_sb_selected(self, msg):
        """
        Observes toggle between surface brightness or flux selection for
        spectrum viewer to trigger translation.
        """

        if msg.get('name') == 'flux_or_sb_selected':
            self._translate(self.flux_or_sb_selected)

    @observe('flux_unit_selected')
    def _on_flux_unit_changed(self, msg):

        """ Handle changes in selected flux unit."""

        # may need to be updated if translations in other configs going to be supported
        if not hasattr(self, 'flux_unit'):
            return
        if not self.flux_unit.choices and self.app.config == 'cubeviz':
            return

        flux_or_sb = None

        if msg.get('name') != 'flux_unit_selected':
            # not sure when this would be encountered but keeping as a safeguard
            return

        # when the configuration is Specviz, translation is not currently supported.
        # If in Cubeviz, all spectra pass through Spectral Extraction plugin and will
        # have a scale factor assigned in the metadata, enabling translation.
        current_y_unit = self.spectrum_viewer.state.y_display_unit
        if self.angle_unit.selected and check_if_unit_is_per_solid_angle(current_y_unit):
            flux_or_sb = self._append_angle_correctly(
                         self.flux_unit.selected,
                         self.angle_unit.selected
            )
        else:
            flux_or_sb = self.flux_unit.selected
        untranslatable_units = self._untranslatable_units
        # disable translator if flux unit is untranslatable,
        # still can convert flux units, this just disables flux
        # to surface brightnes translation for units in list.
        if flux_or_sb in untranslatable_units:
            self.can_translate = False
        else:
            self.can_translate = True

        yunit = _valid_glue_display_unit(flux_or_sb, self.spectrum_viewer, 'y')

        if self.spectrum_viewer.state.y_display_unit != yunit:
            self.spectrum_viewer.state.y_display_unit = yunit
            self.spectrum_viewer.reset_limits()
            self.hub.broadcast(GlobalDisplayUnitChanged("flux", flux_or_sb, sender=self))

        if not check_if_unit_is_per_solid_angle(self.spectrum_viewer.state.y_display_unit):
            self.flux_or_sb_selected = 'Flux'
        else:
            self.flux_or_sb_selected = 'Surface Brightness'

        # for displaying message that PIXAR_SR = 1 if it is not found in the FITS header
        if (
            len(self.app.data_collection) > 0
            and not self.app.data_collection[0].meta.get('PIXAR_SR')
        ):
            self.pixar_sr_exists = False

    def _translate(self, flux_or_sb=None):
        # currently unsupported, can be supported with a scale factor
        if self.app.config == 'specviz':
            return

        # we want to raise an error if a user tries to translate with an
        # untranslated Flux unit using the API
        untranslatable_units = units_to_strings(self._untranslatable_units)

        if hasattr(self, 'flux_unit'):
            if ((self.flux_unit.selected in untranslatable_units)
                    and (flux_or_sb == 'Surface Brightness')):
                raise ValueError(
                    "Selected flux unit is not translatable. Please choose a flux unit "
                    f"that is not in the following list: {untranslatable_units}."
                )

        if self.spectrum_viewer.state.y_display_unit:
            spec_units = u.Unit(self.spectrum_viewer.state.y_display_unit)
        else:
            return
        # on instantiation, we set determine flux choices and selection
        # after surface brightness
        if not self.flux_unit.choices:
            return
        # Surface Brightness -> Flux
        if check_if_unit_is_per_solid_angle(spec_units) and flux_or_sb == 'Flux':
            spec_units *= u.sr
            # update display units
            self.spectrum_viewer.state.y_display_unit = str(spec_units)

        # Flux -> Surface Brightness
        elif (not check_if_unit_is_per_solid_angle(spec_units)
              and flux_or_sb == 'Surface Brightness'):
            spec_units /= u.sr
            # update display units
            self.spectrum_viewer.state.y_display_unit = str(spec_units)
        # entered the translator when we shouldn't translate
        else:
            return

        self.hub.broadcast(GlobalDisplayUnitChanged('flux',
                                                    spec_units,
                                                    sender=self))
        self.spectrum_viewer.reset_limits()

    @property
    def _untranslatable_units(self):
        return [
            u.erg / (u.s * u.cm**2),
            u.erg / (u.s * u.cm**2 * u.Angstrom),
            u.erg / (u.s * u.cm**2 * u.Hz),
            u.ph / (u.Angstrom * u.s * u.cm**2),
            u.ph / (u.s * u.cm**2 * u.Hz),
            u.ST, u.bol
        ]

    def _append_angle_correctly(self, flux_unit, angle_unit):
        if angle_unit not in ['pix', 'sr']:
            self.sb_unit_selected = flux_unit
            return flux_unit
        if '(' in flux_unit:
            pos = flux_unit.rfind(')')
            sb_unit_selected = flux_unit[:pos] + ' ' + angle_unit + flux_unit[pos:]
        else:
            # append angle if there are no parentheses
            sb_unit_selected = flux_unit + ' / ' + angle_unit

        if sb_unit_selected:
            self.sb_unit_selected = sb_unit_selected

        return sb_unit_selected
