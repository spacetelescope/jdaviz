import gc
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
            # Try to remove the need for finally
            # (why isn't cleanup working elsewhere?)
            self.cleanup()

        return True

    @property
    def output(self):
        if getattr(self, '_output', None) is None:
            self._output = fits.open(self.input)
        return self._output

    def cleanup(self):
        if self.input is None:
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
        gc.collect()
