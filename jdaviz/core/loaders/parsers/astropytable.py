import warnings
from functools import cached_property, partial
from pathlib import Path

from astropy.io import fits
from astropy.io import registry
from astropy.io.fits import VerifyError
from astropy.table import Table, QTable
import numpy as np

from jdaviz.core.loaders.parsers import BaseParser
from jdaviz.core.registries import loader_parser_registry


__all__ = ['AstropyTableParser']
PREFERRED_ASCII_FORMATS = ['ascii',
                           'ascii.csv',
                           'ascii.ecsv',
                           'ascii.tab',
                           'ascii.no_header']


@loader_parser_registry('astropy.Table')
class AstropyTableParser(BaseParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This will function as a user input format
        self.read_format = ''

    @property
    def is_valid(self):

        if self._app.config not in ('deconfigged', 'imviz', 'mastviz'):
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

        # fits files can be successfully opened with table.read
        # try to reject fits files from being validated as catalogs
        # by trying to open the input with fits.open, and rejecting
        # it as a catalog type if it opens successfully
        # eventually we may want to accept BinTableHDU/TableHDU
        # inside fits so this logic should be improved then
        if isinstance(self.input, (fits.ImageHDU, fits.HDUList, fits.PrimaryHDU, fits.CompImageHDU)):  # noqa
            return False
        elif isinstance(self.input, np.ndarray):
            # arrays can be loaded as tables, skip these so images/spectra
            # aren't mis-identified as catalogs
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

    @cached_property
    def is_text_file(self, blocksize=4096):
        """
        Check if the file is a text file. This is used to determine
        if the input is compatible with Astropy's ascii reader.
        """
        try:
            with open(self.input, "rb") as f:
                chunk = f.read(blocksize)
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

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
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                table = QTable.read(self.input, format=fmt)
                exception_text = ''

                if len(w) > 0:
                    # suspicious parse
                    exception_text = 'Table parsed with warnings'

                if len(table) <= 1:
                    exception_text = 'Table is empty'

                if len(table.colnames) <= 1:
                    exception_text = 'Table has no columns'

                table.meta['exception'] = exception_text

        except Exception as e:
            table = QTable(meta={'exception': str(e)})

        return table

    @property
    def input_ext_format(self):
        """
        Parse self.input to determine the format based on its
        file extension to be given to Qtable.read.
        """

        if isinstance(self.input, str):
            input_as_path = Path(self.input)
            suffixes = input_as_path.suffixes
            if len(suffixes) > 1:
                input_ext = ''.join(suffixes)
            else:
                input_ext = suffixes[0]

            # suffixes are returned as '.format'
            input_ext = input_ext.lstrip('.')
            all_formats = registry.get_formats(data_class=QTable, readwrite='Read')['Format']

            # Try ascii first because several format types
            # are deprecated in favor of ascii.format
            if f'ascii.{input_ext}' in all_formats:
                return f'ascii.{input_ext}'

            # Next check the exact file extension
            if input_ext in all_formats:
                return input_ext

            # Next fallback to ascii for text files
            if self.is_text_file:
                return 'ascii'

            # finally fallback to None to allow 'auto-identifying' formats before failing
            return None

        return None

    @property
    def lazy_format_read_results(self):
        """
        Lazy-evaluate attempts to use QTable.read for all valid formats for self.input.

        Stores a bound method for each available format that will execute
        the full try/except logic of _try_qtable_read when invoked.
        """

        all_formats = list(
            registry.get_formats(data_class=QTable, readwrite='Read')['Format']
        ) + [None]  # include None for auto-identification

        return {fmt: partial(self._try_qtable_read, fmt) for fmt in all_formats}

    @cached_property
    def output(self):
        read_format = self.input_ext_format if self.read_format == '' else self.read_format
        # Invoke the lazy-evaluated method to get the table for the desired format
        return self.lazy_format_read_results[read_format]()
