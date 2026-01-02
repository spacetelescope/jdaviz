import numpy as np
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum
from traitlets import Bool, List, observe
import warnings

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           SpectrumInputExtensionsMixin,
                                           _spectrum_assign_component_type)
from jdaviz.core.unit_conversion_utils import to_flux_density_unit
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumImporter']


@loader_importer_registry('1D Spectrum')
class SpectrumImporter(BaseImporterToDataCollection, SpectrumInputExtensionsMixin):
    template_file = __file__, "./spectrum1d.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']
    multiselect = Bool(True).tag(sync=True)
    data_label_suffices = List().tag(sync=True)

    concatenate = Bool(False).tag(sync=True)  # only applicable if multiselect=True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set default data-label
        self._on_extension_change()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False
        if not len(self.extension.choices):
            return False
        try:
            if np.any([spectrum.flux.ndim != 1 for spectrum in self.spectra]):
                return False
        except Exception:
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    def _apply_kwargs(self, kwargs):
        applied_kwargs = super()._apply_kwargs(kwargs)
        if 'extension' not in applied_kwargs and len(self.extension.choices) > 1:
            msg_str = (f"The default extension selection ({self.extension.selected}) will be used.\n"  # noqa
                       f"To load additional sources, please specify them via dropdown or "
                       f"as follows:\n'{self.config}.load(filename, extension=[...]).")
            msg = SnackbarMessage(msg_str, color='warning', sender=self, timeout=10000)
            self.app.hub.broadcast(msg)
            warnings.warn(msg_str)
        return applied_kwargs

    @property
    def user_api(self):
        expose = ['extension', 'unc_extension', 'mask_extension',
                  'concatenate']
        return ImporterUserApi(self, expose)

    @property
    def supported_flux_ndim(self):
        return 1

    @property
    def default_data_label_prefix(self):
        if self.default_data_label_from_resolver:
            return self.default_data_label_from_resolver
        else:
            return '1D Spectrum'

    @observe('extension_items',
             'extension_selected',
             'concatenate')
    def _on_extension_change(self, change={}):
        # override SpectrumInputExtensionsMixin method to handle concatenate case
        self._clear_cache('spectra')

        if not hasattr(self, 'extension'):
            return
        self.data_label_is_prefix = (self.multiselect
                                     and len(self.extension.selected) > 1
                                     and not self.concatenate)
        # data_label_is_prefix is set in SpectrumInputExtensionsMixin,
        # but may be updated after this
        if not hasattr(self, 'extension'):
            self.data_label_default = self.default_data_label_prefix
        elif self.multiselect and len(self.extension.selected) > 1 and self.concatenate:
            self.data_label_default = f"{self.default_data_label_prefix}_concat"
        elif self.multiselect and len(self.extension.selected) == 1 and len(self.extension.choices) > 1:  # noqa
            item_dict = self.extension.selected_item_list[0]
            self.data_label_default = f"{self.default_data_label_prefix}_{item_dict['suffix']}"
        else:
            self.data_label_default = self.default_data_label_prefix
            if self.multiselect and len(self.extension.selected) > 1:
                self.data_label_suffices = [f"_{item_dict['suffix']}" for item_dict in
                                            self.extension.selected_item_list]

    @property
    def output(self):
        # if the entire uncert. array is Nan and the data is not, model fitting won't
        # work (more generally, if uncert[i] is nan/inf and flux[i] is not, fitting will
        # fail, but just deal with the all nan case here since it is straightforward).
        # set uncerts. to None if they are all nan/inf, and display a warning message.
        output = []
        for data in self.spectra:
            if data.uncertainty is not None:
                uncerts_finite = np.isfinite(data.uncertainty.array)
                if not np.any(uncerts_finite):
                    data.uncertainty = None
                    set_nans_to_none = True

                    if set_nans_to_none:
                        # alert user that we have changed their all-nan uncertainty array to None
                        msg = 'All uncertainties are nonfinite, replacing with uncertainty=None.'
                        self.app.hub.broadcast(SnackbarMessage(msg,
                                                               color="warning",
                                                               sender=self.app))
            output.append(data)

        if self.concatenate and len(output) > 1:
            # Vectorized collection of all wavelengths, fluxes, and uncertainties
            wl_list = []
            fnu_list = []
            dfnu_list = []
            for spec in self.spectra:
                wl = spec.spectral_axis.value
                fnu = spec.flux.value

                if spec.uncertainty is not None:
                    dfnu = spec.uncertainty.array
                else:
                    dfnu = np.full_like(fnu, np.nan)

                wl_list.append(wl)
                fnu_list.append(fnu)
                dfnu_list.append(dfnu)

            wlallorig = np.concatenate(wl_list)
            fnuallorig = np.concatenate(fnu_list)
            dfnuallorig = np.concatenate(dfnu_list)

            wave_units = spec.spectral_axis.unit
            pixar_sr = getattr(spec, 'meta', {}).get('PIXAR_SR', 1.0)
            flux_units = to_flux_density_unit(spec.flux.unit, pixar_sr)

            return [combine_lists_to_1d_spectrum(wlallorig,
                                                 fnuallorig,
                                                 dfnuallorig,
                                                 wave_units,
                                                 flux_units)]

        return output

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)

    def __call__(self):
        if not self.extension.selected:
            raise ValueError("No extension selected.")

        with self.app._jdaviz_helper.batch_load():
            for spec_obj, item_dict in zip(self.output, self.extension.selected_item_list):
                if self.data_label_is_prefix:
                    data_label = f"{self.data_label_value}_{item_dict['suffix']}"
                else:
                    data_label = self.data_label_value
                self.add_to_data_collection(spec_obj, data_label,
                                            data_hash=item_dict.get('data_hash'))


def combine_lists_to_1d_spectrum(wl, fnu, dfnu, wave_units, flux_units):
    """
    Combine lists of 1D spectra into a composite `~specutils.Spectrum` object.

    Parameters
    ----------
    wl : list of `~astropy.units.Quantity`s
        Wavelength in each spectral channel
    fnu : list of `~astropy.units.Quantity`s
        Flux in each spectral channel
    dfnu : list of `~astropy.units.Quantity`s or None
        Uncertainty on each flux

    Returns
    -------
    spec : `~specutils.Spectrum`
        Composite 1D spectrum.
    """
    # COPIED FROM specviz.plugins.parsers since cannot import
    wlallarr = np.array(wl)
    fnuallarr = np.array(fnu)
    srtind = np.argsort(wlallarr)
    if dfnu is not None:
        dfnuallarr = np.array(dfnu)
        fnuallerr = dfnuallarr[srtind]
    wlall = wlallarr[srtind]
    fnuall = fnuallarr[srtind]

    # units are not being handled properly yet.
    if dfnu is not None:
        unc = StdDevUncertainty(fnuallerr * flux_units)
    else:
        unc = None

    spec = Spectrum(flux=fnuall * flux_units, spectral_axis=wlall * wave_units,
                    uncertainty=unc)
    return spec
