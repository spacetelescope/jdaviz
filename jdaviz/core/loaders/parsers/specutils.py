import numpy as np

from astropy import units as u
from functools import cached_property
from specutils import Spectrum, SpectrumList

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry
from jdaviz.utils import standardize_metadata


__all__ = ['SpecutilsSpectrumParser',
           'SpecutilsSpectrumArrayParser',
           'SpecutilsSpectrumListParser']


@loader_parser_registry('specutils.Spectrum')
class SpecutilsSpectrumParser(BaseParser):
    SpecutilsCls = Spectrum

    def _check_is_valid(self):
        # generalized jdaviz isn't the valid config name, but we can
        # drop it here for the string output.
        accepted_configs = ['specviz', 'specviz2d', 'cubeviz', 'generalized jdaviz']
        if self._app.config not in ['deconfigged'] + accepted_configs:
            # NOTE: temporary during deconfig process
            return f"specutils.Spectrum format is only supported in {', '.join(accepted_configs)}."

        _ = self.output
        return ''

    @cached_property
    def output(self):
        return self.SpecutilsCls.read(self.input)


@loader_parser_registry('specutils.Spectrum(array)')
class SpecutilsSpectrumArrayParser(SpecutilsSpectrumParser):
    def _check_is_valid(self):
        if not (isinstance(self.input, np.ndarray)
                and self.input.ndim in (1, 2, 3)):
            return 'Input must be a numpy array with 1, 2, or 3 dimensions.'

        return super()._check_is_valid()

    @cached_property
    def output(self):
        arr = self.input

        if not hasattr(arr, 'unit'):
            arr = arr << u.count

        meta = standardize_metadata({})
        # Default to last axis in array for the spectral axis
        msg = "Spectral axis index not specified, assuming last axis."
        self._app.hub.broadcast(SnackbarMessage(msg, sender=self, color="warning"))
        spectral_axis_index = arr.ndim - 1
        return Spectrum(flux=arr, meta=meta, spectral_axis_index=spectral_axis_index)


@loader_parser_registry('specutils.SpectrumList')
class SpecutilsSpectrumListParser(SpecutilsSpectrumParser):
    SpecutilsCls = SpectrumList

    def _check_is_valid(self):
        if self._app.config not in ('deconfigged', 'specviz'):
            return 'specutils.SpectrumList format is only supported in specviz, generalized jdaviz.'
        result = super()._check_is_valid()
        if result:
            return result
        if len(self.output) <= 1:
            return 'SpectrumList must contain more than one spectrum.'
        return ''

    @cached_property
    def output(self):
        return self.SpecutilsCls.read(self.input, flux_col='flux')
