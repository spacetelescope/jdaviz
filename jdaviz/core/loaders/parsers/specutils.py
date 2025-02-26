from functools import cached_property
from specutils import Spectrum1D, SpectrumList

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['SpecutilsSpectrumParser', 'SpecutilsSpectrumListParser']


@loader_parser_registry('specutils.Spectrum')
class SpecutilsSpectrumParser(BaseParser):
    SpecutilsCls = Spectrum1D

    @property
    def is_valid(self):
        if self.app.config not in ('specviz', 'specviz2d'):
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


@loader_parser_registry('specutils.SpectrumList')
class SpecutilsSpectrumListParser(SpecutilsSpectrumParser):
    SpecutilsCls = SpectrumList

    @property
    def is_valid(self):
        if self.app.config != 'specviz':
            # NOTE: temporary during deconfig process
            return False
        return super().is_valid and len(self.output) > 1
