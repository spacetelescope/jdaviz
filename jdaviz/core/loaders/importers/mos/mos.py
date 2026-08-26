import os
from pathlib import Path

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['MOSImporter']


_SPECTRUM_1D_SUFFIXES = ('_x1d.fits', '_x1d.fit', '_x1d.fits.gz', '_x1d.fit.gz')
_SPECTRUM_2D_SUFFIXES = ('_s2d.fits', '_s2d.fit', '_s2d.fits.gz', '_s2d.fit.gz',
                         '_cal.fits', '_cal.fit', '_cal.fits.gz', '_cal.fit.gz',
                         '_c1d.fits', '_c1d.fit', '_c1d.fits.gz', '_c1d.fit.gz')
_IMAGE_SUFFIXES = ('_i2d.fits', '_i2d.fit', '_i2d.fits.gz', '_i2d.fit.gz')
_CAT_SUFFIXES = ('_cat.ecsv', '_cat.csv', '_cat.fits', '_cat.fit', '_cat.ecsv.gz')
_IGNORE_SUFFIXES = ('manifest.html', 'readme', 'readme.md', 'readme.txt')
_MOS_PRODUCT_SUFFIXES = _SPECTRUM_1D_SUFFIXES + _SPECTRUM_2D_SUFFIXES + _IMAGE_SUFFIXES + _CAT_SUFFIXES + _IGNORE_SUFFIXES  # noqa


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

        input_path = Path(self.input).expanduser()
        if not input_path.is_dir():
            return 'MOS importer input must be a directory.'

        # to be valid, the directory must contain at least one 1D spectrum
        # and no extraneous/invalid files
        has_spectrum_1d = False
        for path in input_path.rglob('*'):
            if path.name.startswith('.') or not path.is_file():
                continue
            filename = path.name.lower()
            if not filename.endswith(_MOS_PRODUCT_SUFFIXES):
                return f"Input directory contains unsupported MOS file: {path.name}"
            if filename.endswith(_SPECTRUM_1D_SUFFIXES):
                has_spectrum_1d = True

        if has_spectrum_1d:
            return ''

        return 'Input directory does not contain any MOS 1D spectra matching *_x1d.fits.'

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
