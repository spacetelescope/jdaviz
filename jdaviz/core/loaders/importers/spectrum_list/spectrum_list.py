import itertools
import numpy as np
from copy import deepcopy
import warnings

from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection
from traitlets import List, Bool, Any, observe

from jdaviz.core.unit_conversion_utils import (to_flux_density_unit,
                                               spectrum_ensure_flux_density_unit)
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           _spectrum_assign_component_type)
from jdaviz.core.template_mixin import SelectFileExtensionComponent
from jdaviz.core.user_api import ImporterUserApi
from jdaviz.core.events import SnackbarMessage


__all__ = ['SpectrumListImporter', 'SpectrumListConcatenatedImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    sources_items = List().tag(sync=True)
    sources_selected = Any().tag(sync=True)
    sources_multiselect = Bool(True).tag(sync=True)

    input_in_sb = Bool(False).tag(sync=True)
    convert_to_flux_density = Bool(True).tag(sync=True)

    disable_dropdown = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

        sources_options = []

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

                label = f"{exposure_label}, Source ID: {name}"
                # Flipping the two from the variable naming convention
                name_ver = f"{ver}_{name}"
                suffix = f"EXP-{ver}_ID-{name}"

            else:
                name_ver = index
                name = index
                ver = index
                label = f"1D Spectrum at index: {index}"
                suffix = f"index-{index}"

            sources_options.append({'label': label,
                                    'index': index,
                                    'name': str(name),
                                    'ver': str(ver),
                                    'name_ver': str(name_ver),
                                    'suffix': suffix,
                                    'obj': self._apply_spectral_mask(spec)})

        self.sources = SelectFileExtensionComponent(self,
                                                    items='sources_items',
                                                    selected='sources_selected',
                                                    multiselect='sources_multiselect',
                                                    manual_options=sources_options)

        self.sources.selected = [self.sources.choices[0]]
        self._sources_items_helper = deepcopy(self.sources.items)

        # TODO: This observer will likely be removed in follow-up effort
        # If the resolver format is set to "1D Spectrum List", then we
        # only enable the import button if at least one spectrum is selected.
        self.resolver.observe(self._on_format_selected_change, names='format_selected')

    def _apply_kwargs(self, kwargs):
        applied_kwargs = super()._apply_kwargs(kwargs)
        if 'sources' not in applied_kwargs:
            msg_str = (f"The default source selection ({self.sources.selected}) will be used.\n"
                       f"To load additional sources, please specify them via dropdown or "
                       f"as follows:\n'{self.config}.load(filename, sources = [...]).")
            msg = SnackbarMessage(msg_str, color='warning', sender=self, timeout=10000)
            self.app.hub.broadcast(msg)
            warnings.warn(msg_str)
        return applied_kwargs

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def user_api(self):
        expose = ['sources', 'convert_to_flux_density']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz'):
            # NOTE: temporary during deconfig process
            return False
        # TODO: should this be split into two loaders?
        # should a loader take a single input type, output a single output type,
        # or just have a consistent data_label and viewer?

        # If the input is a SpectrumList or SpectrumCollection, it
        # must be non-empty.
        if isinstance(self.input, (SpectrumList, SpectrumCollection)):
            return len(self.input) > 0

        return self._is_2d_spectrum

    @observe('sources_selected')
    def _on_sources_selected_change(self, change={}):
        if len(self.sources_selected) == 0:
            self.import_disabled = True
        else:
            self.import_disabled = False

            self.input_in_sb = bool(np.any([sp.flux.unit.physical_type == 'surface brightness'
                                            for sp in self.sources.selected_obj]))

    def _on_format_selected_change(self, change={}):
        if change['new'] == '1D Spectrum List':
            # Only perform this check if the selected importer is SpectrumListImporter
            # Otherwise other valid importers (in the case of Spectrum2D)
            # will also run and reset import_disabled
            if 'SpectrumListImporter' in str(type(self)).split('.')[-1]:
                self._on_sources_selected_change()

        elif change['new'] == '1D Spectrum Concatenated':
            # 2D Spectra load all for concatenated
            if self._is_2d_spectrum:
                self.import_disabled = False
            else:
                self._on_sources_selected_change()

        else:
            self.import_disabled = False

    def input_to_list_of_spec(self, inp):

        def this_row(field, i):
            if field is None:
                return None
            return field[i, :]

        if isinstance(inp, Spectrum):
            if inp.flux.ndim == 1:
                return [self._apply_spectral_mask(inp)]

            return [Spectrum(spectral_axis=inp.spectral_axis,
                             flux=this_row(inp.flux, i),
                             uncertainty=this_row(inp.uncertainty, i),
                             mask=this_row(inp.mask, i),
                             meta=inp.meta)
                    for i in range(inp.flux.shape[0])]

        elif isinstance(inp, (SpectrumList, SpectrumCollection)):
            return itertools.chain(*[self.input_to_list_of_spec(spec) for spec in inp])

        else:
            raise NotImplementedError(f"{inp} is not supported")

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None
        if self.input_in_sb and self.convert_to_flux_density:
            return [spectrum_ensure_flux_density_unit(sp) for sp in self.sources.selected_obj]
        else:
            return self.sources.selected_obj

    @staticmethod
    def is_wfssmulti(spec):
        return 'WFSSMulti' in spec.meta.get('header', {}).get('DATAMODL', '')

    @staticmethod
    def _extract_exposure_sourceid(spec):
        """
        Generate a label for WFSSMulti sources based on the header information.
        """
        header = spec.meta.get('header', {})
        exp_num = header.get('EXPGRPID', '0_0_0').split('_')[-2]
        source_id = str(spec.meta.get('source_id', ''))

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

    @property
    def _is_2d_spectrum(self):
        return isinstance(self.input, Spectrum) and self.input.flux.ndim == 2

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

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)

    def __call__(self):
        if not self.sources.selected:
            raise ValueError("No sources selected.")

        with self.app._jdaviz_helper.batch_load():
            for spec_obj, item_dict in zip(self.output, self.sources.selected_item_list):
                data_label = f"{self.data_label_value}_{item_dict['suffix']}"
                self.add_to_data_collection(spec_obj, data_label)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.select_all_for_concatenation = False

        if self._is_2d_spectrum:
            self.disable_dropdown = True
            # If we select_all() here, then if the user switches back to Spectrum List
            # all items will be selected, which is not the desired behavior.
            self.select_all_for_concatenation = True
            # Enable the import button upon initialization because otherwise having
            # no sources selected will disable it for other valid importers (e.g. Image).
            self.import_disabled = False

    @property
    def output(self):
        if self.select_all_for_concatenation:
            self.sources.select_all()

        spectrum_list = self.sources.selected
        if len(spectrum_list) == 0:
            return []

        # Vectorized collection of all wavelengths, fluxes, and uncertainties
        wl_list = []
        fnu_list = []
        dfnu_list = []
        for spec in self.sources.selected_obj:
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

        return combine_lists_to_1d_spectrum(wlallorig,
                                            fnuallorig,
                                            dfnuallorig,
                                            wave_units,
                                            flux_units)

    def __call__(self):
        data_label = self.data_label_value
        self.add_to_data_collection(self.output, f"{data_label}")

        # Do we need to reset in case user switches back to Spectrum List?
        # self.sources.selected = []
