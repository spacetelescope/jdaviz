from functools import cached_property
from regions import Regions
from specutils import SpectralRegion

from jdaviz.core.region_translators import is_stcs_string, stcs_string2region
from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['RegionsParser']


@loader_parser_registry('Regions')
class RegionsParser(BaseParser):
    @property
    def is_valid(self):
        if isinstance(self.input, str):
            if is_stcs_string(self.input):
                return True
            ext = self.input.split('.')[-1]
            if self.app.config == 'imviz':
                return ext in ('reg', 'fits')
            elif self.app.config in ('specviz', 'specviz2d'):
                return ext == 'ecsv'
            return ext in ('reg', 'fits', 'ecsv')

    @cached_property
    def output(self):
        region_format = None
        if is_stcs_string(self.input):
            return stcs_string2region(self.input)
        try:
            return Regions.read(self.input, format=region_format)
        except Exception:  # nosec
            return SpectralRegion.read(self.input)
