import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from numpy.testing import assert_allclose

from jdaviz.core.crossmatch import (crossmatch_pair, crossmatch_catalogs,
                                    apply_review_decisions)


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
        review_factor=2.0,
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
        review_factor=2.0,
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
        review_factor=2.0,
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
        review_factor=2.0,
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

    res = crossmatch_pair(base, other, tolerance=1 * u.arcsec, review_factor=2.0)

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
