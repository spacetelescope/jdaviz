from functools import cached_property
import asdf
import warnings

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
        if self.app.config not in ('deconfigged', 'imviz'):
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
        else:
            warnings.warn(
                f"{self.input} should be opened with the `roman_datamodels` package, "
                "which is not installed in this environment. To install optional "
                "jdaviz dependencies for Roman, you can run:  \n\n"
                "pip install -U jdaviz[roman]\n\n"
                "This file will be loaded with the `asdf` package instead.\n\n",
                UserWarning
            )
        return asdf.open(self.input)
