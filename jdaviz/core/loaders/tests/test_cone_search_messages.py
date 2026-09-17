import pytest
from astropy.table import Table
from astropy.utils.data import conf as data_conf


CONE_SEARCH_RESOLVERS = ['astroquery', 'virtual observatory']


class TestConeSearchMessages:
    """
    Each cone-search resolver is set up with a resolvable source so that
    ``query_archive`` only depends on the (patched) ``_query_single_coord``,
    and both resolvers are expected to report results identically.
    """

    @pytest.fixture(autouse=True, params=CONE_SEARCH_RESOLVERS)
    def setup_method(self, request, deconfigged_helper):
        self.helper = deconfigged_helper
        self.ldr = deconfigged_helper.loaders[request.param]._obj
        self.ldr.source = '337.5 -20.8'
        self.calls = []

    def _query_msg_texts(self, color=None):
        return [item['text'] for item in self.ldr.query_message_items
                if color is None or item['color'] == color]

    def _query_msg_tracebacks(self, color=None):
        return [repr(item['traceback']) for item in self.ldr.query_message_items
                if color is None or item['color'] == color]

    def _fail_first(self, coord):
        self.calls.append(coord)
        if len(self.calls) == 1:
            raise RuntimeError('service is down')
        return Table({'flux': [1]})

    @pytest.mark.parametrize('max_results, n_output, expected_msg, hit_cap',
                             [(None, 3, '3 results found.', False),
                              (2, 2, 'maximum limit set (2).', True)])
    def test_success_reported(self, max_results, n_output, expected_msg, hit_cap):
        """
        A successful query is reported as a success banner which is also broadcast
        as a snackbar and recorded in the logger history.
        """
        ldr = self.ldr
        if max_results is not None:
            ldr.max_results = max_results
        ldr._query_single_coord = lambda coord: Table({'flux': [1, 2, 3]})

        ldr.query_archive()

        assert ldr.returned_no_results is False
        assert ldr.returned_max_results is hit_cap
        assert len(ldr._output) == n_output
        success_msgs = self._query_msg_texts('success')
        assert len(success_msgs) == 1
        assert success_msgs[0].endswith(expected_msg)

        # every banner message is also broadcast as a snackbar/recorded in the logger
        assert [m['text'] for m in self.helper.plugins['Logger'].history] == self._query_msg_texts()
        assert [m['color'] for m in self.helper.plugins['Logger'].history] == [
            d['color'] for d in ldr.query_message_items]

    def test_no_results_reported(self):
        ldr = self.ldr
        ldr._query_single_coord = lambda coord: None

        ldr.query_archive()

        assert ldr.returned_no_results is True
        assert ldr._output is None
        assert any(text.startswith('The search returned no results')
                   for text in self._query_msg_texts('error'))
        # the queried archive/resource (when known) is identified in the message
        archive = ldr._query_archive_label.strip()
        if archive:
            assert any(f'no results from {archive}' in text
                       for text in self._query_msg_texts('error'))

    def test_query_failure_reported(self):
        """A failing query is reported rather than raised, in both resolvers."""
        ldr = self.ldr

        ldr._query_single_coord = self._fail_first

        ldr.query_archive()

        assert ldr.returned_no_results is True
        assert len(self._query_msg_texts('error')) == len(self._query_msg_tracebacks('error')) == 1
        assert 'service is down' in self._query_msg_tracebacks('error')[0]

        # a subsequent query clears the failure banner and is this time successful
        ldr._query_single_coord = lambda coord: Table({'flux': [1]})
        ldr.query_archive()
        assert self._query_msg_texts('error') == []
        assert len(self._query_msg_texts('success')) == 1

    def test_query_message_raise_behavior(self):
        """``raise_msg`` warns for warnings and raises errors that carry a traceback."""
        ldr = self.ldr

        with pytest.warns(UserWarning, match='heads up'):
            ldr._query_message('heads up', color='warning', raise_msg=True)

        with pytest.raises(ValueError, match='fatal'):
            ldr._query_message('fatal', color='error',
                               traceback=ValueError('fatal'), raise_msg=True)

        # an error without a traceback can only be reported, never raised
        ldr._query_message('reported only', color='error', raise_msg=True)
        assert 'reported only' in self._query_msg_texts('error')

    def test_unresolvable_source_reported(self):
        """Name resolution failures are reported rather than raised, in both resolvers."""
        ldr = self.ldr
        ldr.source = 'ThisIsAFakeTarget'

        calls = []
        ldr._query_single_coord = lambda coord: calls.append(coord)

        # disabling astropy's internet access makes Sesame name resolution fail immediately
        with data_conf.set_temp('allow_internet', False):
            ldr.query_archive()

        assert ldr.returned_no_results is True
        assert calls == []
        # Check both message text and traceback for the error
        assert any(f'Unable to resolve source name: {ldr.source}' in text
                   for text in self._query_msg_texts('error'))
        assert any('All Sesame queries failed' in tb for tb in self._query_msg_tracebacks('error'))

    def test_catalog_mode_failure_identifies_source(self, sky_coord_only_source_catalog):
        """A failure on one catalog row is reported per-source and does not abort the loop."""
        ldr = self.ldr
        self.helper.load(sky_coord_only_source_catalog, format='Catalog')
        label = [d.label for d in self.helper._app.data_collection
                 if d.meta.get('_importer') == 'CatalogImporter'][-1]
        ldr.search_input.selected = 'Catalog'
        ldr.catalog.selected = label

        ldr._query_single_coord = self._fail_first

        ldr.query_archive()

        # all rows are still queried and the surviving results are kept
        assert len(self.calls) == len(sky_coord_only_source_catalog)
        assert len(ldr._output) == len(sky_coord_only_source_catalog) - 1
        errors = self._query_msg_texts('error')
        tracebacks = self._query_msg_tracebacks('error')
        assert len(errors) == len(tracebacks) == 1
        # the failing source is identified by its catalog row label, not by ldr.source
        assert f"{float(sky_coord_only_source_catalog['ra'][0]):.6f}" in errors[0]
        assert 'service is down' in tracebacks[0]
