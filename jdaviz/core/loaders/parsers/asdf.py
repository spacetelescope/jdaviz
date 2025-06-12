from functools import cached_property
import asdf

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True

__all__ = ['ASDFParser']


@loader_parser_registry('asdf')
class ASDFParser(BaseParser):

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d', 'lcviz', 'imviz'):
            # NOTE: temporary during deconfig process
            return False

        try:
            self.output
        except Exception:
            return False

        return True

    @cached_property
    def output(self):
        if HAS_ROMAN_DATAMODELS:
            return rdd.open(self.input)
        return asdf.open(self.input)
