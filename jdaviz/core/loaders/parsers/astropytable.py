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

    @property
    def input_format(self):
        """Parse input to determine the format to be given to Qtable.read."""

        if isinstance(self.input, str):
            input_as_path = Path(self.input)
            suffixes = input_as_path.suffixes
            if len(suffixes) > 1:
                input_ext = ''.join(suffixes)
            else:
                input_ext = suffixes[0]

            # suffixes are returned as '.format'
            input_ext = input_ext.lstrip('.')
            available_formats = registry.get_formats(data_class=QTable, readwrite='Read')['Format']

            # Try ascii first because several format types
            # are deprecated in favor of ascii.format
            if f'ascii.{input_ext}' in available_formats:
                return f'ascii.{input_ext}'

            elif input_ext in available_formats:
                return input_ext

        # passing None will allow 'auto-identifying' formats before failing
        return None

    @cached_property
    def all_possible_format_results(self):
        all_format_results = {}

        all_formats = registry.get_formats(data_class=QTable, readwrite='Read')['Format']
        for fmt in all_formats:
            try:
                table = QTable.read(self.input, format=fmt)
                table.meta['exception'] = ''
            except Exception as e:
                table = QTable(meta={'exception': str(e)})

            all_format_results[fmt] = table

        return all_format_results

    @cached_property
    def output(self):
        read_format = self.input_format if self.read_format == '' else self.read_format
        return self.all_possible_format_results[read_format]
