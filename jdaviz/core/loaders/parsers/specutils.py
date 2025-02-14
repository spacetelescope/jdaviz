from functools import cached_property
from specutils import Spectrum1D, SpectrumList

from jdaviz.core.registries import loader_parser_registry


@loader_parser_registry('specutils.Spectrum')
class SpecutilsSpectrumParser():
    SpecutilsCls = Spectrum1D

    @property
    def is_valid(self):
        try:
            self.object
        except Exception as e:
            print(f"{self.SpecutilsCls.__name__} read failed", str(e))
            return False
        return True

    @cached_property
    def object(self):
        if isinstance(self.input, self.SpecutilsCls):
            return self.input
        return self.SpecutilsCls.read(self.input)

    def __call__(self):
        return self.object


@loader_parser_registry('specutils.SpectrumList')
class SpecutilsSpectrumListParser(SpecutilsSpectrumParser):
    SpecutilsCls = SpectrumList

    @property
    def is_valid(self):
        return super().is_valid and len(self.object) > 1