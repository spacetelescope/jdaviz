from packaging.version import Version

import specutils
from astropy import units as u
from astropy.nddata import VarianceUncertainty, StdDevUncertainty, InverseVariance
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage
from traitlets import List, Unicode, Any, observe

from jdaviz.core.events import SnackbarMessage, RedshiftMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list)
from jdaviz.configs.specviz.helper import _apply_redshift_to_spectra

__all__ = ['UnitConversion']

unit_exponents = {StdDevUncertainty: 1,
                  InverseVariance: -2,
                  VarianceUncertainty: 2}
SPECUTILS_GT_1_7_0 = Version(specutils.__version__) > Version('1.7.0')


@tray_registry('g-unit-conversion', label="Unit Conversion",
               viewer_requirements='spectrum')
class UnitConversion(PluginTemplateMixin, DatasetSelectMixin):

    template_file = __file__, "unit_conversion.vue"

    current_flux_unit = Unicode().tag(sync=True)
    current_spectral_axis_unit = Unicode().tag(sync=True)
    new_flux_unit = Any().tag(sync=True)
    new_spectral_axis_unit = Any().tag(sync=True)

    spectral_axis_unit_equivalencies = List([]).tag(sync=True)
    flux_unit_equivalencies = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, SubsetCreateMessage, handler=self._on_viewer_subset_changed)
        self.hub.subscribe(self, SubsetDeleteMessage, handler=self._on_viewer_subset_changed)

        self._redshift = None
        self.app.hub.subscribe(self, RedshiftMessage, handler=self._redshift_listener)

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )

        # when accessing the selected data, access the spectrum-viewer version
        # TODO: we'll probably want to update unit-conversion to be able to act on cubes directly
        # in the future
        self.dataset._viewers = [self._default_spectrum_viewer_reference_name]
        # require entries to be in spectrum-viewer (not other cubeviz images, etc)
        self.dataset.add_filter('layer_in_spectrum_viewer')

    def _on_viewer_subset_changed(self, *args):
        if len(self.app.data_collection.subset_groups) == 0:
            self.disabled_msg = ''
        else:
            self.disabled_msg = 'Please create Subsets only after unit conversion'

    def _redshift_listener(self, msg):
        '''Save new redshifts (including from the helper itself)'''
        if msg.param == "redshift":
            self._redshift = msg.value

    @observe('dataset_selected')
    def update_ui(self, event=None):
        """
        Set up UI to have all values of currently visible spectra.
        """
        spectrum = self.dataset.selected_obj
        if spectrum is None:
            return

        # Set UI label to show current flux and spectral axis units.
        self.current_flux_unit = spectrum.flux.unit.to_string()
        self.current_spectral_axis_unit = spectrum.spectral_axis.unit.to_string()

        # Populate drop down with all valid options for unit conversion.
        self.spectral_axis_unit_equivalencies = create_spectral_equivalencies_list(spectrum)
        self.flux_unit_equivalencies = create_flux_equivalencies_list(spectrum)

    def vue_unit_conversion(self, *args, **kwargs):
        """
        Runs when the ``apply`` button is hit. Tries to change units if ``new`` units are set
        and are valid.
        """
        if self._redshift is not None:
            # apply the global redshift to the new spectrum
            spectrum = _apply_redshift_to_spectra(self.dataset.selected_obj, self._redshift)
        else:
            spectrum = self.dataset.selected_obj

        converted_spec = self.process_unit_conversion(spectrum,
                                                      self.new_flux_unit,
                                                      self.new_spectral_axis_unit)
        if converted_spec is None:
            return

        label = f"_units_copy_Flux:{converted_spec.flux.unit}_" +\
                f"SpectralAxis:{converted_spec.spectral_axis.unit}"
        new_label = ""

        # Finds the '_units_copy_' spectrum and does unit conversions in that copy.
        if "_units_copy_" in self.dataset_selected:

            selected_data_label = self.dataset_selected
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
                self.app.add_data_to_viewer(
                    self.app._default_spectrum_viewer_reference_name,
                    new_label, clear_other_data=True
                )

        else:
            new_label = self.dataset_selected + label

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

        self.app.add_data_to_viewer(
            self.app._default_spectrum_viewer_reference_name,
            new_label, clear_other_data=True
        )
        snackbar_message = SnackbarMessage(
            f"Data set '{label}' units converted successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

    def process_unit_conversion(self, spectrum, new_flux=None, new_spectral_axis=None):
        """

        Parameters
        ----------
        spectrum : `specutils.Spectrum1D`
            The spectrum that will have its units converted.
        new_flux
            The flux of spectrum will be converted to these units if they are provided.
        new_spectral_axis
            The spectral_axis of spectrum will be converted to these units if they are provided.

        Returns
        -------
        converted_spectrum : `specutils.Spectrum1D`
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
            except ValueError as e:
                snackbar_message = SnackbarMessage(
                    "Unable to convert spectral axis units for selected data. "
                    f"Try different units: {repr(e)}",
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
            except ValueError as e:
                snackbar_message = SnackbarMessage(
                    "Unable to convert flux units for selected data. "
                    f"Try different units: {repr(e)}",
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
                                            wcs=None,
                                            spectral_axis=set_spectral_axis_unit,
                                            unit=set_flux_unit.unit,
                                            uncertainty=temp_uncertainty)
        if SPECUTILS_GT_1_7_0:
            converted_spectrum.shift_spectrum_to(redshift=spectrum.redshift)
        else:
            converted_spectrum.redshift = spectrum.redshift
        return converted_spectrum
