from functools import cached_property
from astropy.table import QTable

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['AstropyQTableParser']


@loader_parser_registry('Astropy QTable')
class AstropyQTableParser(BaseParser):
    @property
    def is_valid(self):
        if self.app.config != 'imviz':
            # NOTE: temporary during deconfig process
            return False
        try:
            table = self.output
        except Exception:
            return False
        else:
            return len(table.colnames) > 0

    @cached_property
    def output(self):
        return QTable.read(self.input)
