from astropy.coordinates.builtin_frames import __all__ as all_astropy_frames

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import TableMixin
from jdaviz.core.loaders.resolvers.url import URLResolver
from jdaviz.core.user_api import LoaderUserApi

__all__ = ["QueryResultsResolver"]


@loader_resolver_registry("query results")
class QueryResultsResolver(URLResolver, TableMixin):
    template_file = __file__, "query_results.vue"
    default_input = 'query_results'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._query_results = None

#        self.table.headers_avail = ["Title", "Instrument", "DateObs", "URL"]
#        self.table.headers_visible = ["Title", "Instrument", "DateObs"]

        self.table.show_rowselect = True
        self.table.item_key = "product_key"
        self.table.multiselect = False
        self.table._selected_rows_changed_callback = self._on_table_select_change

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=["query_results", "table"])

    @property
    def query_results(self):
        return self._query_results

    @query_results.setter
    def query_results(self, obj):
        self._query_results = obj
        self._update_format_items()

        self.table.items = []

        for row in obj:
            self.table.add_item(row)

    def _on_table_select_change(self, _=None):
        self._update_format_items()
        self.url = self.selected_url

    @property
    def is_valid(self):
        # this resolver does not accept any direct, (default_input = None), so can
        # always be considered valid
        # TODO: update to check format of input table
        return True

    @property
    def selected_url(self):
        if len(self.table.selected_rows) != 1:
            return None
        selected_row = self.table.selected_rows[0]
        for k in ("url", "URL"):
            if k in selected_row.keys():
                return self.table.selected_rows[0][k]
        for k in ('uri', 'URI'):
            if k in selected_row.keys():
                # TODO: this will need to be more general,
                # or maybe we can offload URI/download to download_uri_to_path
                return 'https://mast.stsci.edu/search/jwst/api/v0.1/retrieve_product?product_name=' + self.table.selected_rows[0][k]
        return ''
