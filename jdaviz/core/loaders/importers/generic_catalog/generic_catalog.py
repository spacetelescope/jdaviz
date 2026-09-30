import numpy as np
from astropy.table import Table, QTable

from jdaviz.core.loaders.importers import BaseCatalogImporter
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['GenericCatalogImporter']


@loader_importer_registry("Generic Catalog")
class GenericCatalogImporter(BaseCatalogImporter):

    template_file = __file__, "./generic_catalog.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_valid:
            return

        # dropdown to select columns to import
        self._init_col_other(self.input.colnames)

    def _check_is_valid(self):
        return self._basic_table_validity_checks(self.input)

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Scatter', 'reference': 'scatter-viewer'},
                {'label': 'Histogram', 'reference': 'histogram-viewer'},
                {'label': 'Table', 'reference': 'table-viewer'}]

    @property
    def user_api(self):

        expose = ['col_other']

        return ImporterUserApi(self, expose=expose)

    @property
    def output_cols(self):

        if not isinstance(self.input, (Table, QTable)):
            return

        return [col for col in set(self.col_other_selected) if col in self.input.colnames]

    @property
    def output(self):

        if not isinstance(self.input, (Table, QTable)):
            return

        table = self.input[self.output_cols]
        output_table = QTable()

        # assign an ID column to the table
        if 'ID' not in self.output_cols:
            output_table['ID'] = np.arange(len(table))
            output_table.meta['_jdaviz_loader_id_col'] = 'ID'

        for col in self.output_cols:
            output_table[col] = table[col]

        return output_table

    def __call__(self):
        super().__call__()
