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

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    @cached_property
    def output(self):
        return self.SpecutilsCls.read(self.input)


@loader_parser_registry('specutils.Spectrum(array)')
class SpecutilsSpectrumArrayParser(SpecutilsSpectrumParser):
    @property
    def is_valid(self):
        return (isinstance(self.input, np.ndarray)
                and self.input.ndim in (1, 2, 3)
                and super().is_valid)

    @cached_property
    def output(self):
        arr = self.input

        if not hasattr(arr, 'unit'):
            arr = arr << u.count

        meta = standardize_metadata({})
        # Default to last axis in array for the spectral axis
        msg = "Spectral axis index not specified, assuming last axis."
        self.app.hub.broadcast(SnackbarMessage(msg, sender=self, color="warning"))
        spectral_axis_index = arr.ndim - 1
        return Spectrum(flux=arr, meta=meta, spectral_axis_index=spectral_axis_index)


@loader_parser_registry('specutils.SpectrumList')
class SpecutilsSpectrumListParser(SpecutilsSpectrumParser):
    SpecutilsCls = SpectrumList

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz'):
            # NOTE: temporary during deconfig process
            return False
        return super().is_valid and len(self.output) > 1

    @cached_property
    def output(self):
        return self.SpecutilsCls.read(self.input, flux_col='flux')
