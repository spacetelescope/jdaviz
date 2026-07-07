import numpy as np
import pytest
from unittest.mock import patch
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from astropy.table import Table

from glue.core.subset import RangeSubsetState

from jdaviz.core.events import SnackbarMessage


class TestCatalogConeSearch:
    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper, sky_coord_only_source_catalog, pixel_coord_source_catalog):
        self.helper = deconfigged_helper
        self.ldr = deconfigged_helper.loaders['astroquery']._obj
        self.sky_catalog = sky_coord_only_source_catalog
        self.pixel_catalog = pixel_coord_source_catalog
        # the source_id string column is used as the "source name" column below
        self.source_names = list(sky_coord_only_source_catalog['source_id'])

    def _load_catalog(self, catalog, **load_kwargs):
        """Load ``catalog`` as a Catalog and return its data collection label."""
        self.helper.load(catalog, format='Catalog', **load_kwargs)
        return [d.label for d in self.helper._app.data_collection
                if d.meta.get('_importer') == 'CatalogImporter'][-1]

    def _enter_catalog_mode(self, catalog=None, col_other=None,
                            col_type='sky_coords', name_col=None):
        """Load a catalog and put the loader into Catalog input mode."""
        catalog = self.sky_catalog if catalog is None else catalog
        kwargs = {'col_other': col_other} if col_other else {}
        label = self._load_catalog(catalog, **kwargs)
        self.ldr.input_select.selected = 'Catalog'
        self.ldr.catalog.selected = label
        self.ldr.catalog_col_type = col_type
        if name_col is not None:
            self.ldr.catalog_name_col.selected = name_col
        return label

    def _capture_snackbars(self):
        """Collect ``SnackbarMessage`` broadcasts on the loader's hub."""
        msgs = []
        self.ldr.hub.subscribe(self.ldr, SnackbarMessage, handler=lambda m: msgs.append(m))
        return msgs

    @staticmethod
    def _fake_query(n_per_source=2):
        """A ``_query_single_coord`` replacement recording each call."""
        calls = []

        def _query(skycoord):
            calls.append(skycoord)
            return Table({'flux': list(range(n_per_source))})

        _query.calls = calls
        return _query

    @staticmethod
    def _fail_from_name(fail_names, error='boom', distinct=False):
        """A ``SkyCoord.from_name`` replacement failing for ``fail_names``."""
        def _fake(name, frame=None):
            name = str(name)
            if name in fail_names:
                raise NameResolveError(f'{error}-{name}' if distinct else error)
            return SkyCoord(1.0, 2.0, unit='deg')
        return _fake

    # --------------------------------------------------------------------

    def test_get_catalog_skycoords(self):
        # Catalog mode is hidden until a catalog is loaded
        assert 'Catalog' not in self.ldr.input_select.labels
        # Source is the default
        assert self.ldr.input_selected == 'Source'

        self._enter_catalog_mode()
        assert 'Catalog' in self.ldr.input_select.labels

        coords = self.ldr._get_catalog_skycoords()
        # each entry is (SkyCoord, source_label, error_string)
        assert len(coords) == len(self.sky_catalog)
        skycoords = SkyCoord([sc for sc, _, _ in coords])
        np.testing.assert_allclose(skycoords.ra.deg, self.sky_catalog['ra'].value)
        np.testing.assert_allclose(skycoords.dec.deg, self.sky_catalog['dec'].value)
        # sky_coords mode labels are the formatted RA/Dec and never carry an error
        assert coords[0][1] == '337.502930000000 -20.814830000000'
        assert all(err is None for _, _, err in coords)

    def test_query_catalog_stacks_results(self):
        self._enter_catalog_mode()
        fake = self._fake_query(n_per_source=2)
        self.ldr._query_single_coord = fake

        self.ldr.query_archive()

        n = len(self.sky_catalog)
        assert len(fake.calls) == n  # one query per catalog row
        assert len(self.ldr._output) == 2 * n  # 2 rows per source, stacked
        idx_col = self.ldr._catalog_source_index_colname
        assert idx_col in self.ldr._output.colnames
        assert sorted(set(self.ldr._output[idx_col])) == list(range(n))
        assert self.ldr.query_progress == ''
        assert self.ldr.returned_no_results is False

        # Check max results
        # max_results caps the stacked output AND stops the loop early, so fewer
        # sources are queried than exist in the catalog.
        self.ldr.max_results = 3
        fake = self._fake_query(n_per_source=2)
        self.ldr._query_single_coord = fake

        self.ldr.query_archive()

        # truncate to max_results == 3
        assert len(fake.calls) == 2
        assert len(fake.calls) < len(self.sky_catalog)
        assert len(self.ldr._output) == 3
        assert self.ldr.returned_max_results is True

        # Check no results
        self.ldr._query_single_coord = lambda skycoord: None
        self.ldr.query_archive()
        assert self.ldr._output is None
        assert self.ldr.returned_no_results is True

    def test_query_catalog_with_subset(self):
        label = self._enter_catalog_mode()
        data = self.helper._app.data_collection[label]
        # subset selecting only rows with ra < 337.5 deg => last two fixture rows
        state = RangeSubsetState(-np.inf, 337.5, data.id['ra'])
        self.helper._app.data_collection.new_subset_group(label='low_ra', subset_state=state)
        assert 'low_ra' in self.ldr.catalog_subset.labels
        self.ldr.catalog_subset.selected = 'low_ra'

        coords = self.ldr._get_catalog_skycoords()
        assert len(coords) == 2
        np.testing.assert_allclose(
            SkyCoord([sc for sc, _, _ in coords]).ra.deg, self.sky_catalog['ra'].value[3:])

        fake = self._fake_query(n_per_source=1)
        self.ldr._query_single_coord = fake
        self.ldr.query_archive()
        assert len(fake.calls) == 2
        assert len(self.ldr._output) == 2

    def test_missing_radec_metadata_raises(self):
        # a catalog imported with only X/Y columns has no RA/Dec metadata
        self._enter_catalog_mode(self.pixel_catalog)
        with pytest.raises(ValueError, match="RA/Dec"):
            self.ldr._get_catalog_skycoords()

    def test_source_name_resolution(self):
        # Resolve some names and fail others. All rows are kept as
        # (SkyCoord|None, name, error|None) so callers can report failures.
        fail = self.source_names[3:]  # last two names fail to resolve

        # Require source name column
        self._enter_catalog_mode(col_other=['source_id'],
                                 col_type='source_name', name_col='')
        with pytest.raises(ValueError, match="source-name column"):
            self.ldr._get_catalog_skycoords()

        # Now with source name column
        self._enter_catalog_mode(col_other=['source_id'],
                                 col_type='source_name', name_col='source_id')
        # the retained string column is offered for source-name resolution
        assert 'source_id' in self.ldr.catalog_name_col.labels

        with patch.object(SkyCoord, 'from_name', side_effect=self._fail_from_name(fail)):
            coords = self.ldr._get_catalog_skycoords()

        assert [lbl for _, lbl, _ in coords] == self.source_names

        for sc, name, err in coords:
            if name in fail:
                assert sc is None and err
            else:
                assert sc is not None and err is None

    @pytest.mark.parametrize("fail_all", [False, True])
    def test_query_catalog_reports_unresolved(self, fail_all):
        # Unresolved names are skipped, recorded in
        # _source_name_query_failures, and summarized in a snackbar.
        fail = self.source_names if fail_all else self.source_names[3:]
        self._enter_catalog_mode(col_other=['source_id'],
                                 col_type='source_name', name_col='source_id')
        snackbars = self._capture_snackbars()
        fake = self._fake_query(n_per_source=1)
        self.ldr._query_single_coord = fake

        with patch.object(SkyCoord, 'from_name', side_effect=self._fail_from_name(fail)):
            self.ldr.query_archive()

        n_total = len(self.source_names)
        n_fail = len(fail)
        n_ok = n_total - n_fail
        # only resolvable sources are actually queried
        assert len(fake.calls) == n_ok
        assert len(self.ldr._source_name_query_failures) == n_fail

        if fail_all:
            assert self.ldr._output is None
            assert self.ldr.returned_no_results is True
        else:
            assert len(self.ldr._output) == n_ok
            assert self.ldr.returned_no_results is False

        # check snackbar
        assert any(f"Could not resolve {n_fail}/{n_total} source names" in m.text
                   and "'source_id' column" in m.text and m.color == 'warning'
                   for m in snackbars)

        # the individual failures can be inspected
        failed_names = [name for f in self.ldr._source_name_query_failures for name in f]
        assert set(failed_names) == set(fail)

    @pytest.mark.parametrize("distinct,expect_hint", [(False, True), (True, False)])
    def test_resolve_source_names_single_reason_snackbar(self, distinct, expect_hint):
        # A single shared error across all failures emits a "single reason" hint
        # (a sign the resolver service may be down). Distinct errors do not.
        self._enter_catalog_mode(col_other=['source_id'],
                                 col_type='source_name', name_col='source_id')
        snackbars = self._capture_snackbars()
        side_effect = self._fail_from_name(self.source_names, distinct=distinct)
        with patch.object(SkyCoord, 'from_name', side_effect=side_effect):
            coords = self.ldr._get_catalog_skycoords()

        # every row failed and is kept with its error string
        assert all(sc is None and err for sc, _, err in coords)
        hint = 'Single reason failure occurred during name resolution'
        assert any(hint in m.text for m in snackbars) is expect_hint
