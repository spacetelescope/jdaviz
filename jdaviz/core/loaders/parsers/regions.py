from functools import cached_property
from regions import Regions
from specutils import SpectralRegion

from jdaviz.core.registries import loader_parser_registry


@loader_parser_registry('Regions')
class RegionsParser():
    def __init__(self, input):
        # TODO: move into base class
        self.input = input

    @property
    def is_valid(self):
        if isinstance(self.input, (Regions, SpectralRegion)):
            return True
        if isinstance(self.input, str):
            ext = self.input.split('.')[-1]
            return ext in ('reg', 'fits', 'ecsv')

    @cached_property
    def object(self):
        if isinstance(self.input, (Regions, SpectralRegion)):
            return self.input
        # region_format = kwargs.pop('region_format', None)
        region_format = None
        try:
            return Regions.read(self.input, format=region_format)
        except Exception:  # nosec
            return SpectralRegion.read(self.input)

    def __call__(self):
        return self.object


