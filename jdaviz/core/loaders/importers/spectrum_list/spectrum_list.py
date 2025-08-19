import itertools
import numpy as np
from copy import deepcopy
import fnmatch

from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection
from traitlets import List, Bool, Any

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.template_mixin import SelectFileExtensionComponent
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumListImporter', 'SpectrumListConcatenatedImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    exposures_items = List().tag(sync=True)
    exposures_selected = Any().tag(sync=True)
    exposures_multiselect = Bool(True).tag(sync=True)

    spectra_items = List().tag(sync=True)
    spectra_selected = Any().tag(sync=True)
    spectra_multiselect = Bool(True).tag(sync=True)

    disable_dropdown = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

        self.fully_masked_spectra = []
        self.previous_data_label_messages = []
        # These need to be set via attribute to work through
        # the loaders infrastructure (via ``helpers.py``)
        self.load_selected = kwargs.pop('load_selected', [])

        if self.is_valid:
            # If the resolver format is set to "1D Spectrum List", then we
            # only enable the import button if at least one spectrum is selected.
            # This is to avoid a user accidentally importing all spectra (API default)
            # when none are selected
            self.resolver.observe(self._on_format_selected_change, names='format_selected')
            # Separately observe changes to the selected spectra
            self.observe(self._on_spectra_selected_change, names='spectra_selected')

            exposures = []
            spectra_options = []

            index_modifier = 0

            if isinstance(self.input, Spectrum):
                speclist_input = SpectrumList(self.input_to_list_of_spec(self.input))
            else:
                speclist_input = self.input

            for index, spec in enumerate(speclist_input):
                if self.is_wfssmulti(spec):
                    # ver, name are stand-ins for exposure and source_id
                    # ver == exposure, name == source_id
                    ver, name = self._extract_exposure_sourceid(spec)
                    exposure_label = f"Exposure {ver}"
                    exposures.append(exposure_label)

                    label = f"{exposure_label}, Source ID: {name}"
                    # Flipping the two from the variable naming convention
                    name_ver = f"{ver}_{name}"
                    _suffix = f"EXP-{ver}_ID-{name}"

                else:
                    name_ver = index
                    name = index
                    ver = index
                    label = f"1D Spectrum at file index: {index}"
                    _suffix = f"file_index-{index}"

                # all == True implies the entire array is masked and unusable
                if self._is_fully_masked(spec):
                    data_label_prefix = self.data_label_value
                    self.fully_masked_spectra.append(f"'{data_label_prefix}_{_suffix}'")
                    index_modifier += 1
                    continue

                # Use modified index here to access the spectrum properly
                # per ``selected_obj_dict`` in SelectFileExtensionComponent.
                # Attempt to indicate to the user (via label and suffix) that
                # the index is not the same as the file index.
                spectra_options.append({'label': label,
                                        'index': index - index_modifier,
                                        'name': str(name),
                                        'ver': str(ver),
                                        'name_ver': str(name_ver),
                                        '_suffix': _suffix,
                                        'obj': self._apply_spectral_mask(spec)})

            if exposures:
                exposures_options = [{'label': exp, 'index': i, 'ver': exp,
                                      'name': exp, 'name_ver': exp}
                                     for i, exp in enumerate(sorted(set(exposures)))]
                self.exposures = SelectFileExtensionComponent(self,
                                                              items='exposures_items',
                                                              selected='exposures_selected',
                                                              multiselect='exposures_multiselect',
                                                              manual_options=exposures_options)
                self.exposures.selected = []

            self.spectra = SelectFileExtensionComponent(self,
                                                        items='spectra_items',
                                                        selected='spectra_selected',
                                                        multiselect='spectra_multiselect',
                                                        manual_options=spectra_options)

            self.spectra.selected = []

    @property
    def user_api(self):
        expose = ['spectra', 'load_selected']
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

    def _on_spectra_selected_change(self, change={}):
        if not len(self.spectra_selected):
            self.resolver.import_disabled = True
        else:
            self.resolver.import_disabled = False

    def _on_format_selected_change(self, change={}):
        if change['new'] == '1D Spectrum List':
            self._on_spectra_selected_change()
        else:
            self.resolver.import_disabled = False

    def input_to_list_of_spec(self, inp):

        def this_row(field, i):
            if field is None:
                return None
            return field[i, :]

        if isinstance(inp, Spectrum):
            if inp.flux.ndim == 1:
                # Note masks (currently) only applied when spectral_axis has missing values
                return [self._apply_spectral_mask(inp)]

            return [Spectrum(spectral_axis=inp.spectral_axis,
                             flux=this_row(inp.flux, i),
                             uncertainty=this_row(inp.uncertainty, i),
                             mask=this_row(inp.mask, i),
                             meta=inp.meta)
                    for i in range(inp.flux.shape[0])]

        elif isinstance(inp, (SpectrumList, SpectrumCollection)):
            return itertools.chain(*[self.input_to_list_of_spec(spec) for spec in inp
                                     if not self._is_fully_masked(spec)])

        else:
            raise NotImplementedError(f"{inp} is not supported")

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None
        return self.spectra.selected_obj_dict

    @staticmethod
    def is_wfssmulti(spec):
        if 'WFSSMulti' in spec.meta.get('header', {}).get('DATAMODL', ''):
            return True
        return False

    @staticmethod
    def _extract_exposure_sourceid(spec):
        """
        Generate a label for WFSSMulti spectra based on the header information.
        """
        header = spec.meta.get('header', {})
        exp_num = header.get('EXPGRPID', '0_0_0').split('_')[-2]
        source_id = spec.meta.get('source_id', '')

        return exp_num, source_id

    @staticmethod
    def _has_mask(spec):
        if hasattr(spec, 'mask'):
            if spec.mask is not None and len(spec.mask):
                return True
        return False

    def _is_fully_masked(self, spec):
        if self._has_mask(spec):
            # all == True implies the entire array is masked and unusable
            if all(spec.mask):
                return True
        return False

    def _apply_spectral_mask(self, spec):
        # The masks (spec.spectral_axis.mask and spec.mask) for WFSS L3 spectra
        # may not be equivalent, so we only apply the spectral_axis mask to avoid
        # a Specutils error. Specutils expects the spectral axis to be strictly
        # increasing/decreasing so applying the 'full' mask may throw that error.
        if self._has_mask(spec.spectral_axis) and not self._is_fully_masked(spec):
            mask = spec.spectral_axis.mask
            # NOTE: Something breaks when the following is attempted instead
            # of the current implementation
            #
            # spec.mask = spec.mask | spec.spectral_axis.mask
            # return spec
            return Spectrum(
                spectral_axis=spec.spectral_axis[~mask],
                flux=spec.flux[~mask],
                uncertainty=spec.uncertainty[~mask],
                mask=mask[~mask],
                meta=spec.meta)

        return spec

    def _load_selected_helper(self):
        """
        This method is used to load the selected spectra based on the
        `load_selected` attribute. It handles both single string inputs
        and lists of strings, allowing for wildcard matching.
        """
        selected = self.load_selected
        if isinstance(self.load_selected, str):
            if '*' in self.load_selected:
                # fnmatch filter handles Unix style wildcards
                selected = fnmatch.filter(self.spectra.choices, self.load_selected)
            else:
                # Assume it is a single data label and convert to a list
                selected = [self.load_selected]

        self.spectra.selected = selected

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-1d-viewer'

    def __call__(self, show_in_viewer=True):
        # For using the loader via API
        if self.load_selected:
            self._load_selected_helper()

        elif not self.spectra.selected:
            raise ValueError("No spectra selected. Please specify the desired spectra "
                             "via the keyword argument 'load_selected'.")

        data_label_prefix = self.data_label_value

        # Only concerned about data labels from the same file/prefix
        existing_data_labels = [data.label for data in self.app.data_collection
                                if data_label_prefix == data.label.split('_EXP-')[0] or
                                data_label_prefix == data.label.split('_file_index-')[0]]

        with self.app._jdaviz_helper.batch_load():
            for spec_dict in self.output:
                data_label = f"{data_label_prefix}_{spec_dict['_suffix']}"

                if data_label in existing_data_labels:
                    # NOTE: may depend on the science use-case
                    # It probably doesn't make sense to disable import entirely
                    # since a user may want to import spectra after subsequent analysis
                    msg = (f"Spectrum with label '{data_label}' already exists in the viewer, "
                           f"skipping. This message will be shown only once.")
                    # Previously chosen spectra remain in the dropdown and will attempt to import
                    # again, so only show the message once.
                    if msg not in self.previous_data_label_messages:
                        self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color="warning"))
                        self.previous_data_label_messages.append(msg)

                    continue

                self.add_to_data_collection(spec_dict['obj'],
                                            data_label,
                                            show_in_viewer=True)

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
    @property
    def output(self):
        if self.load_selected:
            self._load_selected_helper()

        spectrum_list = self.spectra.selected
        if spectrum_list is None or not len(spectrum_list):
            return None

        # Vectorized collection of all wavelengths, fluxes, and uncertainties
        wl_list = []
        fnu_list = []
        dfnu_list = []
        for spec in self.spectra.selected_obj:
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
