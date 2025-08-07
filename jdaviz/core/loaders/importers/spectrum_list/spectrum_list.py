import itertools
import numpy as np

from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection
from traitlets import List, Bool, Any

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.template_mixin import SelectSpectraComponent
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumListImporter', 'SpectrumListConcatenatedImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    spectra_items = List().tag(sync = True)
    spectra_selected = Any().tag(sync = True)
    spectra_multiselect = Bool(True).tag(sync = True)

    disable_dropdown = Bool(False).tag(sync = True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

        self.fully_masked_spectra = []
        self.use_spectra_component = False

        if self.is_valid:
            self.use_spectra_component = True
            spectra_options = []
            index_modifier = 0

            if isinstance(self.input, Spectrum):
                input = SpectrumList(self.input_to_list_of_spec(self.input))
            else:
                input = self.input

            for index, spec in enumerate(input):
                if self.is_wfssmulti(spec):
                    exposure_sourceid, label, suffix = self.generate_wfssmulti_labels(spec)
                else:
                    # Note this would be the original index before 'popping'
                    # the unusable spectra out
                    exposure_sourceid = str(index)
                    label = f"1D Spectrum at index: {index}"
                    suffix = f"index-{index}"

                # all == True implies the entire array is masked and unusable
                if self.is_fully_masked(spec):
                    self.fully_masked_spectra.append(label)
                    index_modifier += 1
                    continue

                spectra_options.append({'label': label,
                                        'index': index - index_modifier,
                                        'exposure_sourceid': exposure_sourceid,
                                        'suffix': suffix,
                                        'obj': self.apply_spectral_mask(spec)})

            self.spectra = SelectSpectraComponent(self,
                                                  items='spectra_items',
                                                  selected='spectra_selected',
                                                  multiselect='spectra_multiselect',
                                                  manual_options=spectra_options)

            self.spectra.selected = []

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

    def input_to_list_of_spec(self, inp):

        def this_row(field, i):
            if field is None:
                return None
            return field[i, :]

        if isinstance(inp, Spectrum):
            if inp.flux.ndim == 1:
                # Note masks (currently) only applied when spectral_axis has missing values
                return [self.apply_spectral_mask(inp)]

            return [Spectrum(spectral_axis = inp.spectral_axis,
                             flux = this_row(inp.flux, i),
                             uncertainty = this_row(inp.uncertainty, i),
                             mask = this_row(inp.mask, i),
                             meta = inp.meta)
                    for i in range(inp.flux.shape[0])]

        elif isinstance(inp, (SpectrumList, SpectrumCollection)):
            return itertools.chain(*[self.input_to_list_of_spec(spec) for spec in inp
                                     if not self.is_fully_masked(spec)])

        else:
            raise NotImplementedError(f"{inp} is not supported")

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None

        return self.spectra.selected_obj_dict

    def is_wfssmulti(self, spec):
        if 'WFSSMulti' in spec.meta.get('header', {}).get('DATAMODL', ''):
            return True
        return False

    def generate_wfssmulti_labels(self, spec):
        """
        Generate a label for WFSSMulti spectra based on the header information.
        """
        header = spec.meta.get('header', {})
        exp_num = header.get('EXPGRPID', '0_0_0').split('_')[-2]
        source_id = spec.meta.get('source_id', '')

        # Returns exposure_sourceid, label, suffix
        return (f'{exp_num}_{source_id}',
                f'Exposure {exp_num}, Source ID: {source_id}',
                f'EXP-{exp_num}_ID-{source_id}')

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
        if self.has_mask(spec.spectral_axis) and not self.is_fully_masked(spec):
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
        data_label_prefix = self.data_label_value
        existing_data_labels = [data.label for data in self.app.data_collection]
        self.previous_data_label_messages = []

        with self.app._jdaviz_helper.batch_load():
            for spec_dict in self.output:
                data_label = f"{data_label_prefix}_{spec_dict['suffix']}"

                if data_label in existing_data_labels:
                    # NOTE: may depend on the science use-case
                    # It probably doesn't make sense to disable import entirely
                    # since a user may want to import spectra after subsequent analysis
                    msg = (f"Spectrum with label '{data_label}' already exists in the viewer, "
                           f"skipping. This message will only be shown once.")
                    # Previously chosen spectra remain in the dropdown and will attempt to import
                    # again, so only show the message once.
                    if msg not in self.previous_data_label_messages:
                        self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color="warning"))
                    self.previous_data_label_messages.append(msg)
                    continue

                self.add_to_data_collection(spec_dict['obj'],
                                            data_label,
                                            show_in_viewer=show_in_viewer)

        if self.fully_masked_spectra:
            self.app.hub.broadcast(SnackbarMessage(
                f"Spectra {', '.join(self.fully_masked_spectra)} are completely masked.",
                sender=self, color="warning"))


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
    disable_dropdown = Bool(True).tag(sync = True)

    @property
    def output(self):
        spectrum_list = self.spectra.manual_options
        if spectrum_list is None:
            return

        # Vectorized collection of all wavelengths, fluxes, and uncertainties
        wl_list = []
        fnu_list = []
        dfnu_list = []
        for spec_dict in spectrum_list:
            spec = self.apply_spectral_mask(spec_dict['obj'])
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
