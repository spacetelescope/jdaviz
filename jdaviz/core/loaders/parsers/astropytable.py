from functools import cached_property
from pathlib import Path

from astropy.io import fits
from astropy.io import registry
from astropy.io.fits import VerifyError
from astropy.table import Table, QTable
import numpy as np

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['AstropyTableParser']


@loader_parser_registry('astropy.Table')
class AstropyTableParser(BaseParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _check_is_valid(self):

        if self._app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return 'astropy.Table format is only supported in imviz, mastviz, generalized jdaviz.'

        if self.input is None:
            return 'Input must not be None.'

        # first, check if this is a Table or QTable object
        if isinstance(self.input, (Table, QTable)):
            if len(self.input) == 0:
                return 'Table is empty.'
            else:
                return ''

        # fits files can be successfully opened with table.read
        # try to reject fits files from being validated as catalogs
        # by trying to open the input with fits.open, and rejecting
        # it as a catalog type if it opens successfully
        # eventually we may want to accept BinTableHDU/TableHDU
        # inside fits so this logic should be improved then
        if isinstance(self.input,
                      (fits.ImageHDU, fits.HDUList, fits.PrimaryHDU, fits.CompImageHDU)):
            return 'Input is a FITS HDU, not a table.'

        elif isinstance(self.input, np.ndarray):
            # arrays can be loaded as tables, skip these so images/spectra
            # aren't mis-identified as catalogs
            return 'Input is a numpy array, not a table.'

        try:
            f = fits.open(self.input)
            f.close()
            return 'Input is a FITS file, not a table.'
        except (OSError, FileNotFoundError, VerifyError):  # noqa
            # if we can't open as fits, continue checking if catalog
            pass

        # next, see if this is a catalog written to a file
        table = self.output
        if len(table) > 0:
            return ''

        return 'Table is empty.'

    @property
    def is_text_file(self, blocksize=4096):
        """
        Check if the file is a text file. This is used to determine
        if the input is compatible with Astropy's ascii reader.
        """
        if not isinstance(self.input, str):
            return False
        try:
            with open(self.input, 'rb') as f:
                chunk = f.read(blocksize)
            chunk.decode('utf-8')
            return True
        except (UnicodeDecodeError, OSError):
            return False

    @property
    def input_ext_format(self):
        """
        Parse self.input to determine the format based on its
        file extension to be given to Qtable.read.

        The flow of formats to check for a file, 'file.ext', is:
          'ascii.ext' -> 'ext' -> None (auto-identify) -> 'ascii'

        ascii.ext - many 'ext' formats are deprecated in favor of 'ascii.ext'
        ext - safe fallback for other formats
        None - Astropy's auto-identify is fairly robust. 'ascii' was previously
               the catch-all but given the limits of our ability to check text files,
               'ascii' may fail where the auto-identify would succeed
               (e.g. shortened extensions such as '.vot' for votable)
        ascii - fallback for text files only, may also be used for files with no extension
                since QTable.read would otherwise fail without a format being specified.
        """

        if isinstance(self.input, str):
            input_ext = Path(self.input).suffix
            if input_ext == '':
                if self.is_text_file:
                    # Force ascii for text files with no extension since QTable.read
                    # will fail on None otherwise.
                    input_ext = 'ascii'
                else:
                    raise ValueError('Input does not have a file extension '
                                     'and its format cannot be determined.')

            # suffixes are returned as '.format'
            input_ext = input_ext.lstrip('.')
            all_formats = registry.get_formats(data_class=QTable, readwrite='Read')['Format']

            # Try ascii first because several format types
            # are deprecated in favor of ascii.format
            if f'ascii.{input_ext}' in all_formats:
                return f'ascii.{input_ext}'

            # Next check the exact file extension
            elif input_ext in all_formats:
                return input_ext

            # No extension match, return None so that output attempts auto-detect
            return None

        return None

    def _try_qtable_read(self, fmt=None):
        """
        Read a table using QTable.read.

        Parameters
        ----------
        fmt : str, optional
            Format to pass to QTable.read.

        Returns
        -------
        Astropy.QTable
            Astropy.QTable object extracted from input (file).
        """

        try:
            table = QTable.read(self.input, format=fmt)
            # exception_text is for the devs.
            # If some format fails on import but Astropy doesn't raise an exception,
            # it's likely a logic issue with selecting a format in input_ext_format.
            exception_text = '' if len(table) else f'Format {fmt}: Table is empty'

        except Exception as e:
            table = QTable()
            exception_text = f'Format {fmt}: {e}'

            if fmt is None and self.is_text_file:
                # If auto-detect (None) failed, try 'ascii' for text files since
                # some text formats are not marked to be auto-identified, e.g.
                # .dat/.txt/.tsv
                try:
                    table = QTable.read(self.input, format='ascii')
                    exception_text = '' if len(table) else f'Format {fmt}: Table is empty'
                except Exception as ee:
                    exception_text += f';\nAlso tried format {fmt}: {ee}'

        table.meta['_jdaviz_exception'] = exception_text
        return table

    @cached_property
    def output(self):
        return self._try_qtable_read(self.input_ext_format)
