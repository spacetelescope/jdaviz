from astropy import units as u
from astropy.nddata import VarianceUncertainty, StdDevUncertainty, InverseVariance
import numpy as np

from specutils import Spectrum1D
from traitlets import List, Unicode, Any

from jdaviz.core.events import SnackbarMessage, RemoveDataMessage, AddDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['UnitConversion']

unit_exponents = {StdDevUncertainty: 1,
                  InverseVariance: -2,
                  VarianceUncertainty: 2}


@tray_registry('g-unit-conversion', label="Unit Conversion")
class UnitConversion(TemplateMixin):

    template = load_template("unit_conversion.vue", __file__).tag(sync=True)

    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)

    current_flux_unit = Unicode().tag(sync=True)
    current_spectral_axis_unit = Unicode().tag(sync=True)
    new_flux_unit = Any().tag(sync=True)
    new_spectral_axis_unit = Any().tag(sync=True)

    spectral_axis_unit_equivalencies = List([]).tag(sync=True)
    flux_unit_equivalencies = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_data = None

        self.spectrum = None

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receieves
        a glue message containing viewer information in the case of the former
        set of events, and updates the available data list displayed to the
        user.

        Notes
        -----
        We do not attempt to parse any data at this point, at it can cause
        visible lag in the application.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        self._viewer_id = self.app._viewer_item_by_reference(
            'spectrum-viewer').get('id')

        # Subsets are global and are not linked to specific viewer instances,
        # so it's not required that we match any specific ids for that case.
        # However, if the msg is not none, check to make sure that it's the
        # viewer we care about.
        if msg is not None and msg.viewer_id != self._viewer_id:
            return

        self._viewer_data = self.app.get_data_from_viewer('spectrum-viewer')

        self.dc_items = [data.label
                         for data in self.app.data_collection
                         if data is not None]

        if self.app.get_viewer("spectrum-viewer").state.reference_data is not None:

            data_label = self.app.get_viewer("spectrum-viewer").state.reference_data.label
            spectrum = self._viewer_data[data_label]

            self.set_spectrum(spectrum, data_label)

        self.update_ui()

    def set_spectrum(self, spectrum, label):
        """
        Set spectrum for unit conversion.

        Parameters
        spectrum : `Spectrum1D`
            Spectrum for unit conversion.
        label : `string`
            Label used to represent spectrum.
        ----------
        """
        self.spectrum = spectrum
        self.selected_data = label

    def vue_data_selected(self, event):

        self.set_spectrum(self.app.data_collection[event].get_object(cls=Spectrum1D), event)

        self.update_ui()

    def update_ui(self):
        """
        Set up UI to have all values of currently visible spectra.
        """
        if len(self._viewer_data) < 1:
            self.selected_data = ""
            self.current_flux_unit = ""
            self.current_spectral_axis_unit = ""
            return

        # Set UI label to show current flux and spectral axis units.
        self.current_flux_unit = self.spectrum.flux.unit.to_string()
        self.current_spectral_axis_unit = self.spectrum.spectral_axis.unit.to_string()

        # Populate drop down with all valid options for unit conversion.
        self.spectral_axis_unit_equivalencies = self.create_spectral_equivalencies_list()
        self.flux_unit_equivalencies = self.create_flux_equivalencies_list()

    def vue_unit_conversion(self, *args, **kwargs):
        """
        Runs when the `apply` button is hit. Tries to change units if `new` units are set
        and are valid.
        """

        converted_spec = self.process_unit_conversion(self.spectrum,
                                                      self.new_flux_unit,
                                                      self.new_spectral_axis_unit)

        label = f"_units_copy_Flux:{converted_spec.flux.unit}_" +\
                f"SpectralAxis:{converted_spec.spectral_axis.unit}"
        new_label = ""

        # Finds the '_units_copy_' spectrum and does unit conversions in that copy.
        if "_units_copy_" in self.selected_data:

            selected_data_label = self.selected_data
            selected_data_label_split = selected_data_label.split("_units_copy_")

            new_label = selected_data_label_split[0] + label

            original_spectrum = self.data_collection[selected_data_label_split[0]]
            original_flux = original_spectrum.get_object().flux.unit
            original_spectral_axis = original_spectrum.get_object().spectral_axis.unit

            if new_label in self.data_collection:
                # Spectrum with these converted units already exists.
                msg = SnackbarMessage(
                    "Spectrum with these units already exists, please check the data drop down.",
                    color="warning",
                    sender=self)
                self.hub.broadcast(msg)
                return

            elif converted_spec.flux.unit == original_flux and \
                    converted_spec.spectral_axis.unit == original_spectral_axis:
                # Check if converted units already exist in the original spectrum.
                msg = SnackbarMessage(
                    "These are the units of the original spectrum, please use "
                    "that spectrum instead.",
                    color="warning",
                    sender=self)
                self.hub.broadcast(msg)
                return

            else:
                # Add spectrum with converted units to app.
                self.app.add_data(converted_spec, new_label)
                self.app.add_data_to_viewer("spectrum-viewer", new_label, clear_other_data=True)

        else:
            new_label = self.selected_data + label

            if new_label in self.data_collection:
                # Spectrum with these converted units already exists.
                msg = SnackbarMessage(
                    "Spectrum with these units already exists, please check the data drop down.",
                    color="warning",
                    sender=self)
                self.hub.broadcast(msg)

                return
            else:

                # Replace old spectrum with new one with updated units.
                self.app.add_data(converted_spec, new_label)

        self.app.add_data_to_viewer("spectrum-viewer", new_label, clear_other_data=True)
        snackbar_message = SnackbarMessage(
            f"Data set '{label}' units converted successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

    def process_unit_conversion(self, spectrum, new_flux=None, new_spectral_axis=None):
        """

        Parameters
        ----------
        spectrum : `Spectrum1D`
            The spectrum that will have its units converted.
        new_flux : ``
            The flux of spectrum will be converted to these units if they are provided.
        new_spectral_axis : ``
            The spectral_axis of spectrum will be converted to these units if they are provided.

        Returns
        -------
        converted_spectrum : `Spectrum1D`
            A new spectrum with converted units.
        """
        set_spectral_axis_unit = spectrum.spectral_axis
        set_flux_unit = spectrum.flux

        current_flux_unit = spectrum.flux.unit.to_string()
        current_spectral_axis_unit = spectrum.spectral_axis.unit.to_string()

        # Try to set new units if set and are valid.
        if new_spectral_axis is not None \
                and new_spectral_axis != "" \
                and new_spectral_axis != current_spectral_axis_unit:
            try:
                set_spectral_axis_unit = spectrum.spectral_axis.to(u.Unit(new_spectral_axis))
            except ValueError:
                snackbar_message = SnackbarMessage(
                    "Unable to convert spectral axis units for selected data. "
                    "Try different units.",
                    color="error",
                    sender=self)
                self.hub.broadcast(snackbar_message)

                return

        # Try to set new units if set and are valid.
        if new_flux is not None \
                and new_flux != "" \
                and new_flux != current_flux_unit:
            try:
                equivalencies = u.spectral_density(set_spectral_axis_unit)
                set_flux_unit = spectrum.flux.to(u.Unit(new_flux),
                                                 equivalencies=equivalencies)
            except ValueError:
                snackbar_message = SnackbarMessage(
                    "Unable to convert flux units for selected data. Try different units.",
                    color="error",
                    sender=self)
                self.hub.broadcast(snackbar_message)

                return

        # Uncertainty converted to new flux units
        if spectrum.uncertainty is not None:
            unit_exp = unit_exponents.get(spectrum.uncertainty.__class__)
            # If uncertainty type not in our lookup, drop the uncertainty
            if unit_exp is None:
                msg = SnackbarMessage(
                    "Warning: Unrecognized uncertainty type, cannot guarantee "
                    "conversion so dropping uncertainty in resulting data",
                    color="warning",
                    sender=self)
                self.hub.broadcast(msg)
                temp_uncertainty = None
            else:
                try:
                    # Catch and handle error trying to convert variance uncertainties
                    # between frequency and wavelength space.
                    # TODO: simplify this when astropy handles it
                    temp_uncertainty = spectrum.uncertainty.quantity**(1/unit_exp)
                    temp_uncertainty = temp_uncertainty.to(u.Unit(set_flux_unit.unit),
                                       equivalencies=u.spectral_density(set_spectral_axis_unit)) # noqa
                    temp_uncertainty **= unit_exp
                    temp_uncertainty = spectrum.uncertainty.__class__(temp_uncertainty.value)
                except u.UnitConversionError:
                    msg = SnackbarMessage(
                        "Warning: Could not convert uncertainty, setting to "
                        "None in converted data",
                        color="warning",
                        sender=self)
                    self.hub.broadcast(msg)
                    temp_uncertainty = None
        else:
            temp_uncertainty = None

        # Create new spectrum with new units.
        converted_spectrum = spectrum._copy(flux=set_flux_unit,
                                            spectral_axis=set_spectral_axis_unit,
                                            unit=set_flux_unit.unit,
                                            uncertainty=temp_uncertainty
                                            )
        return converted_spectrum

    def create_spectral_equivalencies_list(self):
        """
        Gets all possible conversions from current spectral_axis_unit.
        """
        # Get unit equivalencies.
        curr_spectral_axis_unit_equivalencies = u.Unit(
            self.spectrum.spectral_axis.unit).find_equivalent_units(
            equivalencies=u.spectral())

        # Get local units.
        local_units = [u.Unit(unit) for unit in self._locally_defined_spectral_axis_units()]

        # Remove overlap units.
        curr_spectral_axis_unit_equivalencies = list(set(curr_spectral_axis_unit_equivalencies)
                                                     - set(local_units))

        # Convert equivalencies into readable versions of the units and sorted alphabetically.
        spectral_axis_unit_equivalencies_titles = sorted(self.convert_units_to_strings(
            curr_spectral_axis_unit_equivalencies))

        # Concatenate both lists with the local units coming first.
        spectral_axis_unit_equivalencies_titles = sorted(self.convert_units_to_strings(
            local_units)) + spectral_axis_unit_equivalencies_titles

        return spectral_axis_unit_equivalencies_titles

    def create_flux_equivalencies_list(self):
        """
        Gets all possible conversions for flux from current flux units.
        """
        # Get unit equivalencies.
        curr_flux_unit_equivalencies = u.Unit(
            self.spectrum.flux.unit).find_equivalent_units(
            equivalencies=u.spectral_density(np.sum(self.spectrum.spectral_axis)),
                                             include_prefix_units=False) # noqa

        # Get local units.
        local_units = [u.Unit(unit) for unit in self._locally_defined_flux_units()]

        # Remove overlap units.
        curr_flux_unit_equivalencies = list(set(curr_flux_unit_equivalencies)
                                            - set(local_units))

        # Convert equivalencies into readable versions of the units and sort them alphabetically.
        to_str_func = self.convert_units_to_strings
        flux_unit_equivalencies_titles = sorted(to_str_func(curr_flux_unit_equivalencies))

        # Concatenate both lists with the local units coming first.
        flux_unit_equivalencies_titles = sorted(to_str_func(local_units)) + \
                                         flux_unit_equivalencies_titles # noqa

        return flux_unit_equivalencies_titles

    @staticmethod
    def _locally_defined_flux_units():
        """
        list of defined spectral flux density units.
        """
        units = ['Jy', 'mJy', 'uJy',
                 'W / (m2 Hz)',
                 'eV / (s m2 Hz)',
                 'erg / (s cm2)',
                 'erg / (s cm2 um)',
                 'erg / (s cm2 Angstrom)',
                 'erg / (s cm2 Hz)',
                 'ph / (s cm2 um)',
                 'ph / (s cm2 Angstrom)',
                 'ph / (s cm2 Hz)']
        return units

    @staticmethod
    def _locally_defined_spectral_axis_units():
        """
        list of defined spectral flux density units.
        """
        units = ['angstrom', 'nanometer',
                 'micron', 'hertz', 'erg']
        return units

    def convert_units_to_strings(self, unit_list):
        """
        Convert equivalencies into readable versions of the units.

        Parameters
        ----------
        unit_list : list
            List of either `astropy.units` or strings that can be converted
            to `astropy.units`.

        Returns
        -------
        list
            A list of the units with their best (i.e., most readable) string version.
        """
        return [u.Unit(unit).name
                if u.Unit(unit) == u.Unit("Angstrom")
                else u.Unit(unit).long_names[0] if (
                    hasattr(u.Unit(unit), "long_names") and len(u.Unit(unit).long_names) > 0)
                else u.Unit(unit).to_string()
                for unit in unit_list]
