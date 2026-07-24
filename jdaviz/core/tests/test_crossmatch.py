import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from numpy.testing import assert_allclose

from jdaviz.core.crossmatch import (crossmatch_pair, crossmatch_catalogs,
                                    apply_review_decisions, _get_skycoord,
                                    catalogs_from_data_collection,
                                    crossmatch_loaded_catalogs)


def _make_catalogs():
    """Build three synthetic catalogs around the same field.

    A (base): 8 sources, with a global ``source_id``.
    B: same field, shares ids for the first 5 sources, positions jittered by
       ~0.3", plus three extra sources.
    C: position-only (no shared ids), with one deliberately ambiguous source
       (source 6, offset ~1.5") to trigger review.
    """
    rng = np.random.default_rng(42)

    base_ra = 150.0 + rng.uniform(-0.01, 0.01, size=8)
    base_dec = 2.0 + rng.uniform(-0.01, 0.01, size=8)
    cat_a = QTable({
        'source_id': [f'A{i:03d}' for i in range(8)],
        'ra': base_ra * u.deg,
        'dec': base_dec * u.deg,
    })

    # B: jitter ~0.3 arcsec (~8.3e-5 deg), share ids for first 5 sources
    jit = 0.3 / 3600.0
    cat_b = QTable({
        'source_id': [f'A{i:03d}' for i in range(5)] + ['B900', 'B901', 'B902'],
        'ra': np.concatenate([base_ra[:5] + rng.uniform(-jit, jit, 5),
                              150.0 + rng.uniform(-0.01, 0.01, 3)]) * u.deg,
        'dec': np.concatenate([base_dec[:5] + rng.uniform(-jit, jit, 5),
                               2.0 + rng.uniform(-0.01, 0.01, 3)]) * u.deg,
    })

    # C: position only. Source 6 is placed in the grey zone (~1.5 arcsec) to force review.
    grey = 1.5 / 3600.0
    c_ra = base_ra.copy()
    c_dec = base_dec.copy()
    c_ra[6] += grey
    cat_c = QTable({
        'Right Ascension (degrees)': c_ra * u.deg,
        'Declination (degrees)': c_dec * u.deg,
    })

    return [('A', cat_a), ('B', cat_b), ('C', cat_c)]


def test_make_catalogs_sizes():
    catalogs = _make_catalogs()
    (_, cat_a), (_, cat_b), (_, cat_c) = catalogs
    assert len(cat_a) == 8
    assert len(cat_b) == 8
    assert len(cat_c) == 8


def test_crossmatch_catalogs_outer_join():
    catalogs = _make_catalogs()
    merged, review = crossmatch_catalogs(
        catalogs,
        tolerance=1 * u.arcsec,
        review_radius=2 * u.arcsec,
        id_columns={'A': 'source_id', 'B': 'source_id'},
        mode='id_then_sky',
    )

    # expected columns are present
    for col in ('base_idx', 'object_id', 'base_ra', 'base_dec', 'A_idx',
                'B_idx', 'B_sep_arcsec', 'B_status', 'C_idx', 'C_sep_arcsec',
                'C_status', 'match_count', 'needs_review'):
        assert col in merged.colnames

    # the 8 base sources, plus B's three extra (unmatched) sources appended
    assert len(merged) == 8 + 3

    # object ids for the base rows come from catalog A's id column
    assert list(merged['object_id'][:8]) == [f'A{i:03d}' for i in range(8)]

    # first 5 base sources are matched to B by shared id
    assert list(merged['B_status'][:5]) == ['matched'] * 5
    assert np.all(merged['B_idx'][:5] == np.arange(5))

    # C is matched positionally; base source 6 lands in the review grey zone
    assert merged['C_status'][6] == 'review'
    assert_allclose(merged['C_sep_arcsec'][6], 1.5, atol=0.05)

    # the remaining base sources match C essentially on top of each other
    matched_c = [merged['C_status'][i] for i in range(8) if i != 6]
    assert matched_c == ['matched'] * 7

    # only base source 6 needs review, and the review table reflects that
    assert merged['needs_review'][6]
    assert int(np.sum(merged['needs_review'])) == 1
    assert len(review) == 1
    assert review['base_idx'][0] == 6


def test_crossmatch_catalogs_left_join():
    catalogs = _make_catalogs()
    merged, _ = crossmatch_catalogs(
        catalogs,
        tolerance=1 * u.arcsec,
        review_radius=2 * u.arcsec,
        id_columns={'A': 'source_id', 'B': 'source_id'},
        mode='id_then_sky',
        join='left',
    )
    # left join keeps exactly one row per base source (no appended rows)
    assert len(merged) == 8
    assert np.all(merged['base_idx'] == np.arange(8))


def test_crossmatch_catalogs_invalid_join():
    catalogs = _make_catalogs()
    with pytest.raises(ValueError, match="join must be 'left' or 'outer'"):
        crossmatch_catalogs(catalogs, join='inner')


def test_apply_review_decisions_reject():
    catalogs = _make_catalogs()
    merged, review = crossmatch_catalogs(
        catalogs,
        tolerance=1 * u.arcsec,
        review_radius=2 * u.arcsec,
        id_columns={'A': 'source_id', 'B': 'source_id'},
        mode='id_then_sky',
    )
    assert merged['needs_review'][6]
    match_count_before = int(merged['match_count'][6])

    # user rejects C's ambiguous match for base source 6
    resolved = apply_review_decisions(merged, {6: {'C': False}})

    assert resolved['C_idx'][6] == -1
    assert np.isnan(resolved['C_sep_arcsec'][6])
    assert resolved['C_status'][6] == 'rejected'
    assert int(resolved['match_count'][6]) == match_count_before - 1
    # no rows remain flagged for review after the only review item is resolved
    assert not np.any(resolved['needs_review'])

    # the original merged table is left unchanged
    assert merged['C_idx'][6] != -1


def test_apply_review_decisions_accept_keeps_match():
    catalogs = _make_catalogs()
    merged, _ = crossmatch_catalogs(
        catalogs,
        tolerance=1 * u.arcsec,
        review_radius=2 * u.arcsec,
        id_columns={'A': 'source_id', 'B': 'source_id'},
        mode='id_then_sky',
    )
    c_idx_before = merged['C_idx'][6]
    assert merged['needs_review'][6]

    # accepting the candidate keeps the match and confirms it (no longer review)
    resolved = apply_review_decisions(merged, {6: {'C': True}})
    assert resolved['C_idx'][6] == c_idx_before
    assert resolved['C_status'][6] == 'matched'
    assert not np.any(resolved['needs_review'])


def test_crossmatch_pair_matched_review_and_collision():
    # base[0] is isolated; base[1] and base[2] both fall on top of other[1]
    base = SkyCoord(ra=[150.0, 150.0002, 150.0003] * u.deg,
                    dec=[2.0, 2.0, 2.0] * u.deg)
    other = SkyCoord(ra=[150.0, 150.00025] * u.deg,
                     dec=[2.0, 2.0] * u.deg)

    res = crossmatch_pair(base, other, tolerance=1 * u.arcsec, review_radius=2 * u.arcsec)

    # base[0] cleanly matches other[0] and is not part of any collision
    assert res['match_idx'][0] == 0
    assert res['status'][0] == 'matched'
    assert 0 not in res['collisions']

    # base[1] and base[2] both claim other[1] -> many-to-one collision -> review
    assert res['match_idx'][1] == 1
    assert res['match_idx'][2] == 1
    assert res['status'][1] == 'review'
    assert res['status'][2] == 'review'
    assert res['collisions'] == {1, 2}


def test_crossmatch_pair_empty_other():
    base = SkyCoord(ra=[150.0] * u.deg, dec=[2.0] * u.deg)
    other = SkyCoord(ra=[] * u.deg, dec=[] * u.deg)

    res = crossmatch_pair(base, other)
    assert res['match_idx'][0] == -1
    assert res['status'][0] == 'unmatched'
    assert res['collisions'] == set()


# --- _get_skycoord --------------------------------------------------------

def test_get_skycoord_sky_centroid():
    tbl = QTable({'sky_centroid': SkyCoord([150.0, 151.0] * u.deg, [2.0, 3.0] * u.deg)})
    sc = _get_skycoord(tbl)
    assert_allclose(sc.ra.deg, [150.0, 151.0])
    assert_allclose(sc.dec.deg, [2.0, 3.0])


def test_get_skycoord_common_radec_names():
    tbl = QTable({'ra': [150.0] * u.deg, 'dec': [2.0] * u.deg})
    sc = _get_skycoord(tbl)
    assert_allclose(sc.ra.deg, [150.0])


def test_get_skycoord_explicit_columns():
    # position columns with instrument-specific names (e.g. ra_gaia/dec_roman)
    tbl = QTable({'ra_gaia': [150.0, 150.5] * u.deg, 'dec_roman': [2.0, 2.5] * u.deg})
    sc = _get_skycoord(tbl, 'ra_gaia', 'dec_roman')
    assert_allclose(sc.ra.deg, [150.0, 150.5])
    assert_allclose(sc.dec.deg, [2.0, 2.5])


def test_get_skycoord_explicit_missing_column_raises():
    tbl = QTable({'ra_gaia': [150.0] * u.deg, 'dec_gaia': [2.0] * u.deg})
    with pytest.raises(ValueError, match='missing requested column'):
        _get_skycoord(tbl, 'ra_gaia', 'dec_nope')


def test_get_skycoord_no_coords_raises():
    tbl = QTable({'flux': [1.0, 2.0]})
    with pytest.raises(ValueError, match='sky_centroid or RA/Dec'):
        _get_skycoord(tbl)


# --- review_radius --------------------------------------------------------

def test_review_radius_flags_grey_zone():
    base = SkyCoord(ra=[150.0] * u.deg, dec=[2.0] * u.deg)
    other = SkyCoord(ra=[150.0 + 1.5 / 3600.0] * u.deg, dec=[2.0] * u.deg)  # ~1.5"

    # a 1.5" neighbor falls in the tolerance..review_radius band -> review
    res = crossmatch_pair(base, other, tolerance=1 * u.arcsec, review_radius=2 * u.arcsec)
    assert res['status'][0] == 'review'
    assert res['match_idx'][0] == 0

    # shrinking review_radius to == tolerance leaves nothing to review -> unmatched
    res2 = crossmatch_pair(base, other, tolerance=1 * u.arcsec, review_radius=1 * u.arcsec)
    assert res2['status'][0] == 'unmatched'
    assert res2['match_idx'][0] == -1


def test_review_radius_defaults_to_twice_tolerance():
    base = SkyCoord(ra=[150.0] * u.deg, dec=[2.0] * u.deg)
    other = SkyCoord(ra=[150.0 + 1.5 / 3600.0] * u.deg, dec=[2.0] * u.deg)
    # no review_radius -> defaults to 2 * tolerance, so the 1.5" source is review
    res = crossmatch_pair(base, other, tolerance=1 * u.arcsec)
    assert res['status'][0] == 'review'


def test_review_radius_less_than_tolerance_raises():
    base = SkyCoord(ra=[150.0] * u.deg, dec=[2.0] * u.deg)
    with pytest.raises(ValueError, match='review_radius must be >= tolerance'):
        crossmatch_pair(base, base, tolerance=2 * u.arcsec, review_radius=1 * u.arcsec)

    catalogs = [('A', QTable({'ra': [150.0] * u.deg, 'dec': [2.0] * u.deg})),
                ('B', QTable({'ra': [150.0] * u.deg, 'dec': [2.0] * u.deg}))]
    with pytest.raises(ValueError, match='review_radius must be >= tolerance'):
        crossmatch_catalogs(catalogs, tolerance=2 * u.arcsec, review_radius=1 * u.arcsec)


# --- modes ----------------------------------------------------------------

def test_default_mode_is_sky():
    # ids would pair base 'S0' with the *far* other source, but the default (sky)
    # mode ignores ids and matches the nearby source instead.
    base = QTable({'source_id': ['S0'], 'ra': [150.0] * u.deg, 'dec': [2.0] * u.deg})
    other = QTable({'source_id': ['S0', 'S1'],
                    'ra': [150.1, 150.0] * u.deg,   # S0 far, S1 coincident with base
                    'dec': [2.0, 2.0] * u.deg})
    merged, _ = crossmatch_catalogs(
        [('base', base), ('other', other)],
        id_columns={'base': 'source_id', 'other': 'source_id'},
        join='left',
    )
    assert merged['other_idx'][0] == 1        # nearby source, not the id-matched far one
    assert merged['other_status'][0] == 'matched'


def test_mode_id_only():
    base = QTable({'source_id': ['S0', 'S1'],
                   'ra': [150.0, 150.001] * u.deg, 'dec': [2.0, 2.0] * u.deg})
    other = QTable({'source_id': ['S1', 'S9'],
                    'ra': [150.0005, 150.05] * u.deg, 'dec': [2.0, 2.0] * u.deg})
    merged, _ = crossmatch_catalogs(
        [('base', base), ('other', other)],
        id_columns={'base': 'source_id', 'other': 'source_id'},
        mode='id', join='left',
    )
    # only S1 shares an id; the id-less base source is not matched positionally
    assert merged['other_idx'][0] == -1
    assert merged['other_status'][0] == 'unmatched'
    assert merged['other_idx'][1] == 0
    assert merged['other_status'][1] == 'matched'


def test_coord_columns_custom_names():
    base = QTable({'ra_gaia': [150.0, 150.01] * u.deg,
                   'dec_gaia': [2.0, 2.01] * u.deg})
    other = QTable({'ra_roman': [150.00001, 150.01001] * u.deg,
                    'dec_roman': [2.00001, 2.01001] * u.deg})
    merged, _ = crossmatch_catalogs(
        [('base', base), ('other', other)],
        coord_columns={'base': ('ra_gaia', 'dec_gaia'),
                       'other': ('ra_roman', 'dec_roman')},
        join='left',
    )
    assert list(merged['other_status']) == ['matched', 'matched']


# --- structure / edge cases ----------------------------------------------

def test_crossmatch_single_catalog():
    base = QTable({'ra': [150.0, 150.01] * u.deg, 'dec': [2.0, 2.01] * u.deg})
    merged, review = crossmatch_catalogs([('A', base)])
    assert len(merged) == 2
    assert list(merged['base_idx']) == [0, 1]
    assert int(np.sum(merged['match_count'])) == 2
    assert len(review) == 0


def test_outer_join_appended_rows():
    catalogs = _make_catalogs()
    merged, _ = crossmatch_catalogs(
        catalogs, tolerance=1 * u.arcsec, review_radius=2 * u.arcsec,
        id_columns={'A': 'source_id', 'B': 'source_id'}, mode='id_then_sky',
    )
    appended = merged[8:]  # B's three extra sources
    assert len(appended) == 3
    # appended rows carry the originating catalog's ids, matched there and 'absent' elsewhere
    assert list(appended['object_id']) == ['B900', 'B901', 'B902']
    assert list(appended['B_status']) == ['matched'] * 3
    assert list(appended['C_status']) == ['absent'] * 3
    assert list(appended['A_idx']) == [-1] * 3
    assert np.all(appended['match_count'] == 1)
    assert not np.any(appended['needs_review'])


def test_crossmatch_catalogs_collision_flags_review():
    # two nearby base sources whose single best match is the same other source
    base = QTable({'ra': [150.0, 150.00005] * u.deg, 'dec': [2.0, 2.0] * u.deg})
    other = QTable({'ra': [150.000025] * u.deg, 'dec': [2.0] * u.deg})
    merged, review = crossmatch_catalogs([('A', base), ('B', other)],
                                         tolerance=1 * u.arcsec, join='left')
    assert list(merged['B_status']) == ['review', 'review']
    assert int(np.sum(merged['needs_review'])) == 2
    assert len(review) == 2


# --- loaded-catalog helpers (integration with the Catalog loader) ---------

def _load_catalog(helper, table, ra_col='ra', dec_col='dec', id_col=None):
    """Load ``table`` as a catalog and return its new data-collection label."""
    dc = helper._app.data_collection
    before = set(dc.labels)

    ldr = helper.loaders['object']
    ldr.object = table
    ldr.format = 'Catalog'
    ldr.importer.viewer.create_new = 'Table'
    ldr.importer.col_ra.selected = ra_col
    ldr.importer.col_dec.selected = dec_col
    if id_col is not None:
        ldr.importer.col_id.selected = id_col
    ldr.load()

    new = list(set(dc.labels) - before)
    assert len(new) == 1
    return new[0]


def test_catalogs_from_data_collection_and_crossmatch(deconfigged_helper):
    rng = np.random.default_rng(7)
    ra = 150.0 + rng.uniform(-0.01, 0.01, 6)
    dec = 2.0 + rng.uniform(-0.01, 0.01, 6)

    # instrument-specific position column names, as the reviewer described
    cat_a = QTable({'ra_gaia': ra * u.deg, 'dec_gaia': dec * u.deg,
                    'source_id': [f'A{i}' for i in range(6)]})
    jit = 0.3 / 3600.0
    cat_b = QTable({'ra_roman': (ra + rng.uniform(-jit, jit, 6)) * u.deg,
                    'dec_roman': (dec + rng.uniform(-jit, jit, 6)) * u.deg})

    label_a = _load_catalog(deconfigged_helper, cat_a,
                            ra_col='ra_gaia', dec_col='dec_gaia', id_col='source_id')
    label_b = _load_catalog(deconfigged_helper, cat_b,
                            ra_col='ra_roman', dec_col='dec_roman')

    catalogs, coord_columns, id_columns = catalogs_from_data_collection(
        deconfigged_helper._app, [label_a, label_b], names=['A', 'B'])

    # coordinate columns are recovered from the importer metadata
    assert coord_columns['A'] == ('ra_gaia', 'dec_gaia')
    assert coord_columns['B'] == ('ra_roman', 'dec_roman')
    assert id_columns['A'] == 'source_id'

    merged, review = crossmatch_catalogs(catalogs, coord_columns=coord_columns)
    # all 6 base sources match their jittered counterparts positionally
    assert list(merged['B_status'][:6]) == ['matched'] * 6
    assert len(review) == 0


def test_crossmatch_loaded_catalogs_convenience(deconfigged_helper):
    rng = np.random.default_rng(11)
    ra = 150.0 + rng.uniform(-0.01, 0.01, 5)
    dec = 2.0 + rng.uniform(-0.01, 0.01, 5)
    cat_a = QTable({'ra': ra * u.deg, 'dec': dec * u.deg})
    jit = 0.3 / 3600.0
    cat_b = QTable({'ra': (ra + rng.uniform(-jit, jit, 5)) * u.deg,
                    'dec': (dec + rng.uniform(-jit, jit, 5)) * u.deg})

    label_a = _load_catalog(deconfigged_helper, cat_a)
    label_b = _load_catalog(deconfigged_helper, cat_b)

    # positional matching by default (no ids needed)
    merged, review = crossmatch_loaded_catalogs(
        deconfigged_helper._app, [label_a, label_b], names=['A', 'B'])
    assert list(merged['B_status'][:5]) == ['matched'] * 5
    assert len(review) == 0


def test_catalogs_from_data_collection_non_catalog_raises(deconfigged_helper,
                                                          image_2d_wcs):
    from astropy.nddata import NDData
    dc = deconfigged_helper._app.data_collection
    before = set(dc.labels)
    deconfigged_helper.load(NDData(np.ones((4, 4)), wcs=image_2d_wcs))
    label = list(set(dc.labels) - before)[0]

    with pytest.raises(ValueError, match='not a catalog'):
        catalogs_from_data_collection(deconfigged_helper._app, [label])
