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
        if isinstance(self.input, SpectrumList):
            spectra_options = []
            # Pre-emptive check for and application of mask to avoid issues down the line
            for index, spec in enumerate(self.input):
                source_id = spec.meta['source_id']
                label = f"Source ID: {source_id}"

                spectra_options.append({'label': label,
                                        'index': index,
                                        'source_id': source_id})

                # all == True implies the entire array is masked and unusable
                if self.is_fully_masked(spec):
                    self.fully_masked_spectra[f'{source_id} at index {index}'] = spec

            print("options dict created")

            self.spectra = SelectSpectraComponent(self,
                                                  items='spectra_items',
                                                  selected='spectra_selected',
                                                  multiselect='spectra_multiselect',
                                                  manual_options=spectra_options)

            print("choices", self.spectra.choices)

            #
            # self.spectra.selected = self.output #[self.spectra.choices[0]]
            #sleep(60)

        # else:
        #     self._set_default_data_label()

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
                    # For now only applying masks to WFSS L3 spectra
                    # just in case that behavior is not desired elsewhere
                    if self.is_wfssmulti(inp):
                        inp = self.apply_mask(inp)
                    return [inp]

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

        return SpectrumList(input_to_list_of_spec(self.input))

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
        header_info = {}
        if self.is_wfssmulti(spec):
            # Target RA and DEC are the (I believe) center of the WFSS pointing
            # and are the same for all spectra in the list.
            # These are used for default label purposes
            header = spec.meta.get('header', {})
            header_info.update({
                'targ_ra': header.get('TARG_RA', ''),
                'targ_dec': header.get('TARG_DEC', ''),
                'source_xpos': header.get('source_XPOS', ''),
                'source_ypos': header.get('source_YPOS', ''),
            })
        return header_info

    def has_mask(self, spec):
        if hasattr(spec, 'mask'):
            if len(spec.mask):
                return True
        return False

    def is_fully_masked(self, spec):
        if self.has_mask(spec):
            # all == True implies the entire array is masked and unusable
            if all(spec.mask):
                return True
        return False

    def apply_mask(self, spec):
        if self.has_mask(spec) and not self.is_fully_masked(spec):
            mask = spec.mask
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
        # self.spectra_items = self.output
        # self.spectra_selected = self.spectra_items
        with self.app._jdaviz_helper.batch_load():
            for i, spec in enumerate(self.output[20:31]):
                print('iterating')
                # TODO: with WFSS, there are too many to add to the collection
                # Must select beforehand

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

        for spec in spectrum_list:
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
