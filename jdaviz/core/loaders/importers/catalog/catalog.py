from traitlets import Bool, Float, List, Unicode, observe
from astropy.table import QTable

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import AutoTextField, SelectPluginComponent, json_safe_table_item
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['CatalogImporter']


@loader_importer_registry('Catalog')
class CatalogImporter(BaseImporterToDataCollection):
    template_file = __file__, "./catalog.vue"

    col_ra_items = List().tag(sync=True)
    col_ra_selected = Unicode().tag(sync=True)

    col_dec_items = List().tag(sync=True)
    col_dec_selected = Unicode().tag(sync=True)

    cone_search = Bool(False).tag(sync=True)
    cone_search_ra = Float().tag(sync=True)
    cone_search_dec = Float().tag(sync=True)
    cone_search_radius = Float().tag(sync=True)

    col_other_items = List().tag(sync=True)
    col_other_selected = List().tag(sync=True)
    col_other_multiselect = Bool(True).tag(sync=True)

    # QTable converted to items to show in UI table
    headers = List().tag(sync=True)
    items = List().tag(sync=True)

    label_value = Unicode().tag(sync=True)
    label_default = Unicode().tag(sync=True)
    label_auto = Bool(True).tag(sync=True)
    label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_valid:
            return
        all_headers = list(self.input.colnames)

        self.col_ra = SelectPluginComponent(self,
                                            items='col_ra_items',
                                            selected='col_ra_selected',
                                            manual_options=all_headers)

        self.col_dec = SelectPluginComponent(self,
                                             items='col_dec_items',
                                             selected='col_dec_selected',
                                             manual_options=all_headers)

        self.col_other = SelectPluginComponent(self,
                                               items='col_other_items',
                                               selected='col_other_selected',
                                               manual_options=all_headers,
                                               multiselect='col_other_multiselect')

        self.label_default = 'Custom Catalog'
        self.label = AutoTextField(self, 'label_value',
                                   'label_default',
                                   'label_auto',
                                   'label_invalid_msg')

    @property
    def user_api(self):
        expose = ['col_ra', 'col_dec',
                  'cone_search', 'cone_search_ra', 'cone_search_dec', 'cone_search_radius',
                  'col_other', 'label']
        return ImporterUserApi(self, expose=expose)

    @property
    def is_valid(self):
        if self.app.config != 'imviz':
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, QTable)

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'table-viewer'

    @property
    def output_cols(self):
        cols_all = [self.col_ra_selected, self.col_dec_selected] + self.col_other_selected
        return [col for col in set(cols_all) if col in self.input.colnames]

    @property
    def output(self):
        qtable = self.input[self.output_cols]

        from glue.core.data_factories import tabular_data, astropy_tabular_data
        qtable.write('test_table.csv', overwrite=True)
        return astropy_tabular_data('test_table.csv')

    @observe('col_ra_selected', 'col_dec_selected', 'col_other_selected')
    def _update_table_preview(self, event={}):
        output_cols = self.output_cols
        self.headers = [col for col in self.input.colnames if col in output_cols]
        self.items = [{col: json_safe_table_item(col, row[col])
                       for col in output_cols}
                      for row in self.input[:10]]

