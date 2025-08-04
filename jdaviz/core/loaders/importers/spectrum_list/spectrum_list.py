import itertools
import numpy as np
from time import sleep

from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection
from traitlets import List, Bool, Any, observe

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.template_mixin import SelectSpectraComponent
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumListImporter', 'SpectrumListConcatenatedImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    # HDUList-specific options
    spectra_items = List().tag(sync = True)
    spectra_selected = Any().tag(sync = True)
    spectra_multiselect = Bool(True).tag(sync = True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

        self.fully_masked_spectra = {}
        # NOTE: This 'if' statement is here because this class is sometimes instantiated
        # with a str from self.input. Is that intended behavior?
        if isinstance(self.input, (Spectrum, SpectrumList)):
            spectra_options = []
            index_modifier = 0
            # Pre-emptive check for and application of mask to avoid issues down the line
            for index, spec in enumerate(self.input):
                # TODO: get this working for _c1d files as well.
                if self.is_wfssmulti(spec):
                    source_id, exposure_num = self.parse_wfssmulti_header(spec)
                    exposure_sourceid = f'{exposure_num}_{source_id}'
                    label = f'Exposure {exposure_num}, Source ID: {source_id}'
                else:
                    # Note this would be the original index before 'popping'
                    # the unusable spectra out
                    exposure_sourceid = str(index)
                    label = f'Spectrum at index: {index}'

                # all == True implies the entire array is masked and unusable
                if self.is_fully_masked(spec):
                    self.fully_masked_spectra[f'{label} at index {index}'] = spec
                    index_modifier += 1
                    continue

                spectra_options.append({'label': label,
                                        'index': index - index_modifier,
                                        'exposure_sourceid': exposure_sourceid,
                                        'obj': self.apply_spectral_mask(spec)})

            self.spectra = SelectSpectraComponent(self,
                                                  items='spectra_items',
                                                  selected='spectra_selected',
                                                  multiselect='spectra_multiselect',
                                                  manual_options=spectra_options)

            self.spectra.selected = [self.spectra.choices[0]]

        # else:
        #     self._set_default_data_label()

    @property
    def user_api(self):
        expose = ['spectra']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz'):
            # NOTE: temporary during deconfig process
            return False
        # TODO: should this be split into two loaders?
        # should a loader take a single input type, output a single output type,
        # or just have a consistent data_label and viewer?
        return (isinstance(self.input, (SpectrumList, SpectrumCollection))
                or (isinstance(self.input, Spectrum) and self.input.flux.ndim == 2))

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None

        def this_row(field, i):
            if field is None:
                return None
            return field[i, :]

        def input_to_list_of_spec(inp):
            if isinstance(inp, Spectrum):
                if inp.flux.ndim == 1:
                    # Note masks (currently) only applied when spectral_axis has missing values
                    return [self.apply_spectral_mask(inp)]

                return [Spectrum(spectral_axis=inp.spectral_axis,
                                 flux=this_row(inp.flux, i),
                                 uncertainty=this_row(inp.uncertainty, i),
                                 mask=this_row(inp.mask, i),
                                 meta=inp.meta)
                        for i in range(inp.flux.shape[0])]

            elif isinstance(inp, (SpectrumList, SpectrumCollection)):
                return itertools.chain(*[input_to_list_of_spec(spec) for spec in inp
                                         if not self.is_fully_masked(spec)])

            else:
                raise NotImplementedError(f"{inp} is not supported")

        if hasattr(self, 'spectra'):
            selected_spectra = SpectrumList(self.spectra.selected_obj)
        else:
            selected_spectra = self.input

        return SpectrumList(input_to_list_of_spec(selected_spectra))

    # def _get_label_with_index_source_id(self, prefix, index=None, source_id=None):
    #     index_source_id = ",".join([str(e) for e in (index, source_id) if e is not None])
    #     return f"{prefix}[{index_source_id}]" if len(index_source_id) else prefix

# TODO: FIX DATA LABEL ISSUES (see pytest)
    # @observe('spectra_selected', 'data_label_as_prefix')
    # def _set_default_data_label(self, *args):
    #     if self.default_data_label_from_resolver:
    #         prefix = self.default_data_label_from_resolver
    #     else:
    #         prefix = "SpectrumList"
    #
    #     # only a single spectra selected
    #     if hasattr(self, 'targ_ra') and hasattr(self, 'targ_dec'):
    #         self.data_label_default = f"{prefix}_{self.targ_ra}_{self.targ_dec}"
    #     # else:
    #     #     self.data_label_default = prefix
    def is_wfssmulti(self, spec):
        if spec.meta.get('header', {}).get('DATAMODL', '') == 'WFSSMultiSpecModel':
            return True
        return False

    def parse_wfssmulti_header(self, spec):
        # These are used for label purposes
        header = spec.meta.get('header', {})
        return (spec.meta.get('source_id', ''),
                header.get('EXPGRPID', '').split('_')[-2])

    def has_mask(self, spec):
        if hasattr(spec, 'mask'):
            if spec.mask is not None and len(spec.mask):
                return True
        return False

    def is_fully_masked(self, spec):
        if self.has_mask(spec):
            # all == True implies the entire array is masked and unusable
            if all(spec.mask):
                return True
        return False

    def apply_spectral_mask(self, spec):
        # WFSS L3 may have a partially masked spectral axis
        # Specutils expects the spectral axis to be strictly increasing/decreasing
        # so without applying the mask, we would get an error for some spectra.
        if self.has_mask(spec) and not self.is_fully_masked(spec):
            mask = spec.spectral_axis.mask
            return Spectrum(
                spectral_axis = spec.spectral_axis[~mask],
                flux = spec.flux[~mask],
                uncertainty = spec.uncertainty[~mask],
                mask = mask[~mask],
                meta = spec.meta)

        return spec

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-1d-viewer'

    def __call__(self, show_in_viewer=True):
        data_label = self.data_label_value
        with self.app._jdaviz_helper.batch_load():
            for i, spec in enumerate(self.output):
                if hasattr(spec, 'meta'):
                    print('iterating', spec.meta.get('source_id', None))

                # TODO: Ensure WFSS populate the same viewer instead of multiple
                self.add_to_data_collection(spec, f"{data_label}_{i}",
                                            show_in_viewer=show_in_viewer)

        if self.fully_masked_spectra:
            self.app.hub.broadcast(SnackbarMessage(
                f"Spectra with Source ID's {', '.join(self.fully_masked_spectra.keys())} "
                "are completely masked.",
                sender = self, color = "warning"))


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


@loader_importer_registry('1D Spectrum Concatenated')
class SpectrumListConcatenatedImporter(SpectrumListImporter):
    @property
    def output(self):
        spectrum_list = super().output
        if spectrum_list is None:
            return

        wlallorig = []  # to collect wavelengths
        fnuallorig = []  # fluxes
        dfnuallorig = []  # and uncertanties (if present)

        # TODO: Speed this up!!! (likely with parallel framework or vectorization)
        for i, spec in enumerate(spectrum_list):
            spec = self.apply_spectral_mask(spec)
            for wlind in range(len(spec.spectral_axis)):
                wlallorig.append(spec.spectral_axis[wlind].value)
                fnuallorig.append(spec.flux[wlind].value)

                # because some spec in the list might have uncertainties and
                # others may not, if uncert is None, set to list of NaN. later,
                # if the concatenated list of uncertanties is all nan (meaning
                # they were all nan to begin with, or all None), it will be set
                # to None on the final Spectrum
                if spec.uncertainty is not None and spec.uncertainty[wlind] is not None:
                    dfnuallorig.append(spec.uncertainty[wlind].array)
                else:
                    dfnuallorig.append(np.nan)

        wave_units = spec.spectral_axis.unit
        flux_units = spec.flux.unit

        return combine_lists_to_1d_spectrum(wlallorig,
                                            fnuallorig,
                                            dfnuallorig,
                                            wave_units,
                                            flux_units)

    def __call__(self, show_in_viewer=True):
        data_label = self.data_label_value
        self.add_to_data_collection(self.output, f"{data_label}",
                                    show_in_viewer=show_in_viewer)
