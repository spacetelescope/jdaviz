from functools import cached_property
from astropy.io import fits
from specutils import Spectrum1D

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['FITSParser']


@loader_parser_registry('FITS')
class FITSParser(BaseParser):

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False

        try:
            self.output
        except Exception:
            return False

        # do not use FITS if able to load with specutils
        # TODO: implement a priority system and use that instead
        try:
            Spectrum1D.read(self.input)
        except Exception:
            return True
        else:
            return False

    @cached_property
    def output(self):
        return fits.open(self.input)
