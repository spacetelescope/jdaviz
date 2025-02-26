from functools import cached_property
from regions import Regions
from specutils import SpectralRegion

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['RegionsParser']


@loader_parser_registry('Regions')
class RegionsParser(BaseParser):
    @property
    def is_valid(self):
        if self.app.config != 'specviz':
            # NOTE: temporary during deconfig process
            return False
        if isinstance(self.input, str):
            ext = self.input.split('.')[-1]
            # once deconfigging is complete:
            # return ext in ('reg', 'fits', 'ecsv')
            return ext == 'ecsv'

    @cached_property
    def output(self):
        region_format = None
        try:
            return Regions.read(self.input, format=region_format)
        except Exception:  # nosec
            return SpectralRegion.read(self.input)
