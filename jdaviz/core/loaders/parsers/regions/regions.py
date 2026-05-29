from functools import cached_property
from regions import Regions
from specutils import SpectralRegion

from jdaviz.core.region_translators import is_stcs_string, stcs_string2region
from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['RegionsParser']


@loader_parser_registry('Regions')
class RegionsParser(BaseParser):
    def _check_is_valid(self):
        if isinstance(self.input, str):
            if is_stcs_string(self.input):
                return ''

            ext = self.input.split('.')[-1]
            if self._app.config == 'imviz':
                if ext in ('reg', 'fits'):
                    return ''
                return f'Unsupported extension .{ext} for imviz regions.'

            elif self._app.config in ('specviz', 'specviz2d'):
                if ext == 'ecsv':
                    return ''
                return f'Unsupported extension .{ext} for {self._app.config} regions.'

            if ext in ('reg', 'fits', 'ecsv'):
                return ''
            return f'Unsupported extension .{ext} for regions.'

        return 'Input must be a string path or STCS string.'

    @cached_property
    def output(self):
        region_format = None
        if is_stcs_string(self.input):
            return stcs_string2region(self.input)
        try:
            return Regions.read(self.input, format=region_format)
        except Exception:  # nosec
            return SpectralRegion.read(self.input)
