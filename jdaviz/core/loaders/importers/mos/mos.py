import os
import re
from pathlib import Path

from astropy.io import fits

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['MOSImporter']


_SPECTRUM_1D_PATTERN = re.compile(r'_(?:x|c)1d\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_SPECTRUM_2D_PATTERN = re.compile(r'_(?:s2d|cal)\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_IMAGE_PATTERN = re.compile(r'_i2d\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)
_CAT_PATTERN = re.compile(r'_cat\.(?:ecsv(?:\.gz)?|csv|fit(?:s)?)$', re.IGNORECASE)
_IGNORE_PATTERN = re.compile(r'(?:manifest\.html|readme(?:\.md|\.txt)?)$', re.IGNORECASE)
_MOS_PRODUCT_PATTERN = re.compile(
    rf'(?:{_SPECTRUM_1D_PATTERN.pattern}|{_SPECTRUM_2D_PATTERN.pattern}|'
    rf'{_IMAGE_PATTERN.pattern}|{_CAT_PATTERN.pattern}|{_IGNORE_PATTERN.pattern})',
    re.IGNORECASE
)
_FITS_PATTERN = re.compile(r'\.fit(?:s)?(?:\.gz)?$', re.IGNORECASE)


def _check_header(path):
    """
    Cheaply check whether ``path`` could be loaded as any of the supported MOS
    products (image, catalog, 1D spectrum, 2D spectrum) by inspecting only the
    FITS headers. Returns an error string if the file can be ruled out, otherwise
    an empty string. This errs on the side of considering a file valid.
    """
    if not _FITS_PATTERN.search(path.name):
        # non-FITS products (ecsv/csv catalogs) are cheap enough to load later
        return ''

    try:
        with fits.open(path, memmap=True, lazy_load_hdus=True) as hdul:
            for hdu in hdul:
                header = hdu.header
                if header.get('XTENSION', '').strip() in ('BINTABLE', 'TABLE'):
                    return ''
                if header.get('NAXIS', 0) >= 1:
                    return ''
    except Exception as e:  # nosec
        return f"MOS file is not readable as FITS: {path.name} ({e})"

    return f"MOS file does not contain any table or array data: {path.name}"


@loader_importer_registry('MOS')
class MOSImporter(BaseImporterToDataCollection):
    template_file = __file__, "./mos.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']
    allow_directory_input = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _get_supported_viewers():
        return []

    def _check_is_valid(self):
        """
        Checks if the input is a valid MOS directory.

        The output of this method is wrapped by the IsValidWrapper
        helper class that converts the string to an inverted boolean,
        i.e. empty string => True, non-empty string => False
        since the string (when filled) carries error information.
        Furthermore, the actual 'is_valid' check is handled by the ValidatorMixin
        that wraps the check in a try/except statement so that individual
        '_check_is_valid' calls no longer need to catch potential failures.
        """
        if self._app.config not in ['deconfigged', 'generalized jdaviz']:
            # NOTE: temporary during deconfig process
            return "MOS importer is only supported in generalized jdaviz."

        if not self._app.state.dev_mos_loader:
            return "MOS importer is only supported in dev mode."

        if not isinstance(self.input, (str, os.PathLike)):
            return 'MOS importer input must be a directory.'

        # don't attempt to parse directories in the file input
        # when single-clicking on '..' to go up a directory
        if str(self.input).endswith('..'):
            return 'MOS importer input must not end with "..".'

        input_path = Path(self.input).expanduser()
        if not input_path.is_dir():
            return 'MOS importer input must be a directory.'

        # to be valid, the directory must contain at least one 1D spectrum
        # and no extraneous/invalid files
        has_spectrum_1d = False
        paths = []
        for path in input_path.rglob('*'):
            if path.name.startswith('.') or not path.is_file():
                continue
            filename = path.name
            if not _MOS_PRODUCT_PATTERN.search(filename):
                return f"Input directory contains unsupported MOS file: {path.name}"
            if _SPECTRUM_1D_PATTERN.search(filename):
                has_spectrum_1d = True
            if not _IGNORE_PATTERN.search(filename):
                paths.append(path)

        if not has_spectrum_1d:
            return 'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.'

        for path in paths:
            err = _check_header(path)
            if err:
                return err

        return ''

    @property
    def user_api(self):
        expose = []
        return ImporterUserApi(self, expose)

    @property
    def default_data_label_prefix(self):
        return 'MOS'

    @property
    def output(self):
        return self.input
