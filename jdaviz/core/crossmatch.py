import uuid

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable

__all__ = ['crossmatch_pair', 'crossmatch_catalogs', 'apply_review_decisions',
           'catalogs_from_data_collection', 'crossmatch_loaded_catalogs']


def _get_skycoord(table, ra_col=None, dec_col=None):
    """Best-effort SkyCoord extraction, mirroring Catalogs._file_parser conventions.

    If ``ra_col``/``dec_col`` are provided, they are used directly (supporting
    catalogs whose position columns are named e.g. ``ra_gaia``/``dec_roman``).
    Otherwise a ``sky_centroid`` column or a few common RA/Dec column names are
    auto-detected.
    """
    if ra_col is not None and dec_col is not None:
        missing = [c for c in (ra_col, dec_col) if c not in table.colnames]
        if missing:
            raise ValueError(f'Catalog is missing requested column(s): {missing}.')
    elif 'sky_centroid' in table.colnames:
        return SkyCoord(table['sky_centroid'])
    else:
        ra_candidates = ['Right Ascension (degrees)', 'ra', 'RA']
        dec_candidates = ['Declination (degrees)', 'dec', 'DEC']
        ra_col = next((c for c in ra_candidates if c in table.colnames), None)
        dec_col = next((c for c in dec_candidates if c in table.colnames), None)
        if ra_col is None or dec_col is None:
            raise ValueError('Catalog needs sky_centroid or RA/Dec columns.')
    # u.Quantity respects an existing unit and assumes deg only when unitless
    ra = u.Quantity(table[ra_col], u.deg)
    dec = u.Quantity(table[dec_col], u.deg)
    return SkyCoord(ra=ra, dec=dec)


def _get_object_id(table, name, id_columns, row_idx):
    """Return the source id for ``row_idx`` of ``table``.

    Uses the catalog's id column (from ``id_columns``) when available, otherwise
    falls back to a generated UUID so every source still has a unique handle.
    """
    id_columns = id_columns or {}
    col = id_columns.get(name)
    if col is not None and col in table.colnames:
        return str(np.asarray(table[col])[row_idx])
    return str(uuid.uuid4())


def crossmatch_pair(base_coords, other_coords, tolerance=1 * u.arcsec,
                    review_radius=None):
    """Positionally match `other` onto `base`.

    Returns a dict with three index arrays describing, for each base source:
      - match_idx : index into `other` of the nearest neighbor (or -1)
      - sep       : separation to that neighbor (arcsec, NaN if none)
      - status    : 'matched' | 'review' | 'unmatched'
    plus `collisions`: set of base indices that share a best-match `other` source.

    A nearest neighbor within ``tolerance`` is auto-accepted ('matched'); one in
    the ``tolerance < sep <= review_radius`` band is flagged for manual review.
    ``review_radius`` defaults to ``2 * tolerance`` and must be >= ``tolerance``.
    """
    if review_radius is None:
        review_radius = 2 * tolerance
    if review_radius < tolerance:
        raise ValueError('review_radius must be >= tolerance.')

    n_base = len(base_coords)
    match_idx = np.full(n_base, -1, dtype=int)
    sep_arcsec = np.full(n_base, np.nan)
    status = np.array(['unmatched'] * n_base, dtype=object)

    if len(other_coords) == 0 or n_base == 0:
        return dict(match_idx=match_idx, sep=sep_arcsec, status=status, collisions=set())

    idx, sep2d, _ = base_coords.match_to_catalog_sky(other_coords)
    within = sep2d <= tolerance
    review = (sep2d > tolerance) & (sep2d <= review_radius)

    match_idx[within | review] = idx[within | review]
    sep_arcsec[within | review] = sep2d[within | review].to_value(u.arcsec)
    status[within] = 'matched'
    status[review] = 'review'

    # many-to-one collisions: same `other` index claimed by multiple base sources
    claimed = match_idx[match_idx >= 0]
    _, counts = np.unique(claimed, return_counts=True)
    dup_targets = set(np.unique(claimed)[counts > 1].tolist())
    collisions = {i for i in range(n_base)
                  if match_idx[i] in dup_targets}
    for i in collisions:
        status[i] = 'review'

    return dict(match_idx=match_idx, sep=sep_arcsec, status=status, collisions=collisions)


def crossmatch_catalogs(catalogs, tolerance=1 * u.arcsec, review_radius=None,
                        id_columns=None, coord_columns=None, mode='sky', join='outer'):
    """Cross-match N catalogs. The first catalog is treated as the base.
    Each subsequent catalog is matched against the running merged set.
    This generalizes to N catalogs and keeps every step a well-understood
    pairwise problem.

    Ambiguous matches (those needing user confirmation) are returned in a separate
    review table rather than silently accepted or rejected. These include:
        - a nearest neighbor whose separation is in a "grey zone"
        (``tolerance < sep <= review_radius``),
        - many-to-one collisions: two base sources whose best match is the same
          other-catalog source.

    Parameters
    ----------
    catalogs : list of (name, QTable)
        Ordered; first is the base. Each table must yield a SkyCoord.
    tolerance : Quantity (angle)
        Hard positional match radius.
    review_radius : Quantity (angle) or None
        Nearest neighbors with ``tolerance < sep <= review_radius`` are flagged for
        manual review. Defaults to ``2 * tolerance`` and must be >= ``tolerance``.
    id_columns : dict or None
        {catalog_name: id_column_name} for exact id matching.
    coord_columns : dict or None
        {catalog_name: (ra_column, dec_column)} to specify the sky-position columns
        explicitly (e.g. ``('ra_gaia', 'dec_gaia')``). Catalogs not listed fall back
        to auto-detection of a ``sky_centroid`` or common RA/Dec column names.
    mode : {'sky', 'id', 'id_then_sky'}
        Default ``'sky'``. Cross-matching strategy:
        - ``sky`` -- :meth:`~astropy.coordinates.SkyCoord.match_to_catalog_sky`
          plus a separation tolerance (recommended default, since source ids are
          rarely shared across catalogs from different instruments).
        - ``id`` -- exact join on a shared source-id column (fast,
        unambiguous when ids are global).
        - ``id_then_sky`` -- use ids where present, fall back to sky for the rest.
    join : {'outer', 'left'}
        'outer' (default) additionally appends those unmatched sources as new rows with
        ``base_idx == -1`` (a full N-way union). Note: this simple mockup does
        not merge unmatched sources *across* the non-base catalogs with each
        other; each becomes its own row.
        'left' keeps exactly one row per base source; sources in
        catalogs 2..N that match no base source are dropped.


    Returns
    -------
    merged : QTable
        One row per base source (plus appended rows if ``join='outer'``), with
        an ``object_id`` column, <name>_idx and <name>_sep_arcsec columns, a
        match_count, and a needs_review flag. ``object_id`` is taken from the
        originating catalog's id column when available, otherwise a generated
        UUID. For appended (outer-join) rows the id comes from the catalog the
        source was added from.
    review : QTable
        Subset of rows (with context) that need user confirmation.
    """
    if join not in ('left', 'outer'):
        raise ValueError("join must be 'left' or 'outer'")
    id_columns = id_columns or {}
    coord_columns = coord_columns or {}
    if review_radius is None:
        review_radius = 2 * tolerance
    if review_radius < tolerance:
        raise ValueError('review_radius must be >= tolerance.')
    base_name, base_tbl = catalogs[0]
    base_ra_col, base_dec_col = coord_columns.get(base_name, (None, None))
    base_coords = _get_skycoord(base_tbl, base_ra_col, base_dec_col)
    n_base = len(base_tbl)
    other_names = [name for name, _ in catalogs[1:]]

    merged = QTable()
    merged['base_idx'] = np.arange(n_base)
    # object-dtype so appended UUIDs (36 chars) aren't truncated to the base id width
    merged['object_id'] = np.array(
        [_get_object_id(base_tbl, base_name, id_columns, i) for i in range(n_base)],
        dtype=object)
    merged['base_ra'] = base_coords.ra.deg * u.deg
    merged['base_dec'] = base_coords.dec.deg * u.deg
    merged[f'{base_name}_idx'] = np.arange(n_base)
    needs_review = np.zeros(n_base, dtype=bool)
    match_count = np.ones(n_base, dtype=int)

    # remember, per catalog, which `other` rows were consumed (for outer join)
    used_by_cat = {}
    coords_by_cat = {}

    for name, tbl in catalogs[1:]:
        ra_col, dec_col = coord_columns.get(name, (None, None))
        other_coords = _get_skycoord(tbl, ra_col, dec_col)
        coords_by_cat[name] = other_coords
        match_idx = np.full(n_base, -1, dtype=int)
        sep = np.full(n_base, np.nan)
        status = np.array(['unmatched'] * n_base, dtype=object)

        # 1) exact id matching where requested and possible
        used_other = set()
        if mode in ('id', 'id_then_sky') and base_name in id_columns and name in id_columns:
            base_ids = np.asarray(base_tbl[id_columns[base_name]]).astype(str)
            other_ids = np.asarray(tbl[id_columns[name]]).astype(str)
            lut = {v: j for j, v in enumerate(other_ids)}
            for i, bid in enumerate(base_ids):
                j = lut.get(bid)
                if j is not None:
                    match_idx[i] = j
                    sep[i] = base_coords[i].separation(other_coords[j]).arcsec
                    status[i] = 'matched'
                    used_other.add(j)

        # 2) positional fallback for the still-unmatched base rows
        if mode in ('sky', 'id_then_sky'):
            todo = np.where(match_idx < 0)[0]
            if len(todo):
                avail = [j for j in range(len(tbl)) if j not in used_other]
                if avail:
                    res = crossmatch_pair(base_coords[todo], other_coords[avail],
                                          tolerance=tolerance, review_radius=review_radius)
                    for k, i in enumerate(todo):
                        if res['match_idx'][k] >= 0:
                            j = avail[res['match_idx'][k]]
                            match_idx[i] = j
                            sep[i] = res['sep'][k]
                            status[i] = res['status'][k]
                            used_other.add(j)

        merged[f'{name}_idx'] = match_idx
        merged[f'{name}_sep_arcsec'] = sep
        merged[f'{name}_status'] = status
        needs_review |= (status == 'review')
        match_count += (match_idx >= 0).astype(int)
        used_by_cat[name] = used_other

    merged['match_count'] = match_count
    merged['needs_review'] = needs_review

    # outer join: append other-catalog sources that matched no base source
    if join == 'outer':
        # `<base_name>_idx` columns stay -1 (absent from the base catalog), but
        # `base_idx` keeps counting so every appended row gets a unique id.
        idx_cols = [f'{base_name}_idx'] + [f'{n}_idx' for n in other_names]
        next_base_idx = n_base
        for name, tbl in catalogs[1:]:
            oc = coords_by_cat[name]
            unmatched = [j for j in range(len(tbl)) if j not in used_by_cat[name]]
            for j in unmatched:
                row = {col: -1 for col in idx_cols}
                row['base_idx'] = next_base_idx
                next_base_idx += 1
                # id comes from the catalog the source was added from (or a UUID)
                row['object_id'] = _get_object_id(tbl, name, id_columns, j)
                row['base_ra'] = oc[j].ra.deg * u.deg
                row['base_dec'] = oc[j].dec.deg * u.deg
                for n in other_names:
                    row[f'{n}_sep_arcsec'] = np.nan
                    # 'absent' = column n was not involved for this appended row
                    row[f'{n}_status'] = 'matched' if n == name else 'absent'
                row[f'{name}_idx'] = j
                row['match_count'] = 1
                row['needs_review'] = False
                merged.add_row(row)

    review = merged[merged['needs_review']]
    return merged, review


def apply_review_decisions(merged, decisions):
    """Apply user accept/reject decisions back onto a merged cross-match table.

    Parameters
    ----------
    merged : QTable
        The merged table returned by :func:`crossmatch_catalogs`.
    decisions : dict
        ``{base_idx: {catalog_name: bool_accept}}``. Rejected matches have their
        ``<name>_idx`` set to -1, ``<name>_sep_arcsec`` set to NaN, and
        ``<name>_status`` set to ``'rejected'``. Accepted matches that were
        flagged for review are confirmed by setting ``<name>_status`` to
        ``'matched'`` so they no longer count as needing review.

    Returns
    -------
    out : QTable
        A copy of ``merged`` with the decisions applied and the ``match_count``
        and ``needs_review`` summary columns recomputed.
    """
    out = merged.copy()
    for base_idx, per_cat in decisions.items():
        row = np.where(out['base_idx'] == base_idx)[0][0]
        for name, accept in per_cat.items():
            if not accept:
                out[f'{name}_idx'][row] = -1
                out[f'{name}_sep_arcsec'][row] = np.nan
                out[f'{name}_status'][row] = 'rejected'
            elif out[f'{name}_status'][row] == 'review':
                # confirm a reviewed match so it no longer needs review
                out[f'{name}_status'][row] = 'matched'
    # recompute summary columns
    idx_cols = [c for c in out.colnames if c.endswith('_idx') and c != 'base_idx']
    out['match_count'] = np.sum([(out[c] >= 0).astype(int) for c in idx_cols], axis=0)
    status_cols = [c for c in out.colnames if c.endswith('_status')]
    out['needs_review'] = np.any([out[c] == 'review' for c in status_cols], axis=0)
    return out


def catalogs_from_data_collection(app, data_labels, names=None):
    """Assemble cross-match inputs from catalogs already loaded into the app.

    Reads each catalog's glue ``Data`` back into a QTable (via the glue-astronomy
    translator, ``data.get_object(cls=QTable)``) and pulls the standardized
    sky-position and id column names from the Catalog importer's metadata
    (``_jdaviz_loader_ra_col`` / ``_jdaviz_loader_dec_col`` / ``_jdaviz_id_col``).
    This lets :func:`crossmatch_catalogs` run on data that has already gone through
    the loader, regardless of the original column names (e.g. ``ra_gaia``/``dec_roman``).

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        A Jdaviz application instance (i.e. ``plugin.app`` inside a plugin, or
        ``helper._app`` from a config helper).
    data_labels : list of str
        Data-collection labels of the loaded catalogs. The first is treated as
        the base by :func:`crossmatch_catalogs`.
    names : list of str or None
        Display names to use for each catalog (defaults to ``data_labels``).

    Returns
    -------
    catalogs : list of (name, QTable)
        Ready to pass to :func:`crossmatch_catalogs`.
    coord_columns : dict
        ``{name: (ra_column, dec_column)}`` from the importer metadata.
    id_columns : dict
        ``{name: id_column}`` from the importer metadata.

    Raises
    ------
    ValueError
        If ``names`` length mismatches, or a label is not a catalog loaded via
        the Catalog importer.
    """
    dc = app.data_collection
    if names is None:
        names = list(data_labels)
    if len(names) != len(data_labels):
        raise ValueError('names must be the same length as data_labels.')

    catalogs, coord_columns, id_columns = [], {}, {}
    for label, name in zip(data_labels, names):
        data = dc[label]
        meta = getattr(data, 'meta', {}) or {}
        if meta.get('_importer') != 'CatalogImporter':
            raise ValueError(f"Data '{label}' is not a catalog loaded via the "
                             "Catalog importer.")
        catalogs.append((name, data.get_object(cls=QTable)))

        ra_col = meta.get('_jdaviz_loader_ra_col')
        dec_col = meta.get('_jdaviz_loader_dec_col')
        if ra_col and dec_col:
            coord_columns[name] = (ra_col, dec_col)
        id_col = meta.get('_jdaviz_id_col')
        if id_col:
            id_columns[name] = id_col

    return catalogs, coord_columns, id_columns


def crossmatch_loaded_catalogs(app, data_labels, names=None, use_ids=False, **kwargs):
    """Cross-match catalogs already loaded into the app.

    Convenience wrapper around :func:`catalogs_from_data_collection` +
    :func:`crossmatch_catalogs`. Positional (sky) matching is used by default;
    pass ``use_ids=True`` to additionally match on the catalogs' id columns
    (``mode='id_then_sky'``). Any :func:`crossmatch_catalogs` keyword (e.g.
    ``tolerance``, ``review_radius``, ``join``, ``mode``) may be supplied and
    takes precedence.

    The id columns discovered from the loader metadata are always forwarded so
    the ``object_id`` output column is populated from real catalog ids rather
    than generated UUIDs, even when ``use_ids=False`` (i.e. sky-only matching).

    Note: matching by id is only meaningful when the id columns are globally
    consistent across catalogs; ids from different instruments are usually not,
    which is why sky matching is the default.

    Returns
    -------
    merged, review : QTable, QTable
        See :func:`crossmatch_catalogs`.
    """
    catalogs, coord_columns, id_columns = catalogs_from_data_collection(
        app, data_labels, names)
    kwargs.setdefault('coord_columns', coord_columns)
    # id columns from the loader metadata are always forwarded so the ``object_id``
    # output column is populated from real catalog ids (not UUIDs), regardless of
    # whether we actually *match* on ids. ``use_ids`` only controls the match mode.
    # A user-supplied ``id_columns`` kwarg still takes precedence via setdefault.
    kwargs.setdefault('id_columns', id_columns)
    if use_ids:
        kwargs.setdefault('mode', 'id_then_sky')
    return crossmatch_catalogs(catalogs, **kwargs)
