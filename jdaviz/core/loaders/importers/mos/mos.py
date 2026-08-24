import numpy as np
from traitlets import Bool, List, observe

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['MOSImporter']


@loader_importer_registry('MOS')
class MOSImporter(BaseImporterToDataCollection):
    template_file = __file__, "./mos.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    def _check_is_valid(self):
        """
        Checks if the input is a valid 1D spectrum.

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
            return f"MOS importer is only supported in generalized jdaviz."

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
        raise NotImplementedError("MOS importer not yet fully implemented")
