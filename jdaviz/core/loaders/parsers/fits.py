import gc
from functools import cached_property
from astropy.io import fits

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['FITSParser']


@loader_parser_registry('fits')
class FITSParser(BaseParser):

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d', 'lcviz', 'imviz', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False

        try:
            self.output
        except Exception:
            return False
        finally:
            self.cleanup()

        return True

    @cached_property
    def output(self):
        return fits.open(self.input)

    def cleanup(self):
        try:
            del self.output.data
        except Exception:  # nosec
            pass
        try:
            self.output.close()
        except Exception:  # nosec
            pass
        gc.collect()
