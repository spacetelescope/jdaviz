from functools import cached_property
from astropy.io import fits
from astropy.io.fits import VerifyError
from astropy.table import Table, QTable

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['AstropyTableParser']


@loader_parser_registry('Astropy Table')
class AstropyTableParser(BaseParser):

    @property
    def is_valid(self):

        if self.app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return False

        if self.input is None:
            return False

        # first, check if this is a Table or QTable object
        if isinstance(self.input, (Table, QTable)):
            if len(self.input) == 0:
                return False
            else:
                return True

        # fits files can be sucessfully opened with table.read
        # try to reject fits files from being validated as catalogs
        # by trying to open the input with fits.open, and rejecting
        # it as a catalog type if it opens sucessfully
        # eventually we may want to accept BinTableHDU/TableHDU
        # inside fits so this logic should be improved then
        if isinstance(self.input, (fits.ImageHDU, fits.HDUList)):
            return False
        try:
            f = fits.open(self.input)
            f.close()
            return False
        except (OSError, FileNotFoundError, VerifyError):  # noqa
            # if we can't open as fits, continue checking if catalog
            pass

        # next, see if this is a catalog written to a file
        try:
            table = self.output
        except Exception:
            return False
        else:
            return len(table) > 0

        return True

    @cached_property
    def output(self):
        return QTable.read(self.input)
