import itertools
import numpy as np
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['SpectrumListImporter', 'SpectrumListConcatenatedImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

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
                    return [inp]
                return [Spectrum(spectral_axis=inp.spectral_axis,
                                 flux=this_row(inp.flux, i),
                                 uncertainty=this_row(inp.uncertainty, i),
                                 mask=this_row(inp.mask, i),
                                 meta=inp.meta)
                        for i in range(inp.flux.shape[0])]
            elif isinstance(inp, (SpectrumList, SpectrumCollection)):
                return itertools.chain(*[input_to_list_of_spec(spec) for spec in inp])
            else:
                raise NotImplementedError(f"{inp} is not supported")

        return SpectrumList(input_to_list_of_spec(self.input))

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-1d-viewer'

    def __call__(self, show_in_viewer=True):
        data_label = self.data_label_value
        with self.app._jdaviz_helper.batch_load():
            for i, spec in enumerate(self.output):
                self.add_to_data_collection(spec, f"{data_label}_{i}",
                                            show_in_viewer=show_in_viewer)


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
