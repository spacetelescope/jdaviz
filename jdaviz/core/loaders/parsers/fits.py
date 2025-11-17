from functools import cached_property
from astropy.io import fits

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['FITSParser']


@loader_parser_registry('fits')
class FITSParser(BaseParser):

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d',
                                   'lcviz', 'imviz', 'cubeviz',
                                   'rampviz'):
            # NOTE: temporary during deconfig process
            return False

        try:
            self.output
        except Exception:
            return False

        return True

    @cached_property
    def output(self):
        return fits.open(self.input)

    def _cleanup(self):
        if 'output' not in self.__dict__:
            return
        for hdu in self.output:
            try:
                del hdu.data
            except Exception:  # nosec
                pass
        try:
            self.output.close()
        except Exception:  # nosec
            pass
        self._clear_cache('output')
