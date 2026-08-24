"""
query_helpers.py
----------------
User-friendly functions for querying and appending to emission_lines.ecsv.

Examples
--------
>>> from query_helpers import load_db, get_lines

>>> db = load_db()
>>> iron_lines = get_lines(db, name_contains="Fe")
>>> nir_lines = get_lines(db, wave_min=1.0, wave_max=2.5, unit="um")
>>> co_lines = get_lines(db, source="CO.csv")
"""

from functools import lru_cache
import json
import numpy as np
from astropy.table import Table
from astropy import units as u
from pathlib import Path

_DIR = Path(__file__).parent

DB_FILE = str(_DIR / "emission_lines.ecsv")
SCHEMA_FILE = str(_DIR / "schema.yaml")


@lru_cache(maxsize=1)
def _load_db_cached(db_file):
    return Table.read(db_file, format="ascii.ecsv")


def load_db():
    """Load the consolidated database as an astropy Table.

    The loaded table is cached at module scope per db_file path so repeated
    resolver instances in the same process reuse one in-memory table.
    """
    # NOTE: if ever accepting multiple different files,
    # we would need to increase maxsize on lru_cache
    return _load_db_cached(DB_FILE)


def clear_db_cache():
    """Clear the module-level database cache."""
    _load_db_cached.cache_clear()


def get_extra_info(row):
    """Parse a row's extra_info JSON string into a plain Python dict."""
    return json.loads(row["extra_info"]) if row["extra_info"] else {}


def get_lines(db, name_contains=None, source=None, wave_min=None, wave_max=None, unit="Angstrom",
              extra_filters=None, element=None, science_case=None):
    """
    Return a filtered copy of the database.

    Parameters
    ----------
    db : astropy.table.Table
        The loaded database (from load_db()).
    name_contains : str, optional
        Case-insensitive substring match on line_name, e.g. "Fe" or "CO".
    source : str, optional
        Restrict to rows from one original source file, e.g. "CO.csv".
    wave_min, wave_max : float, optional
        Wavelength bounds.
    unit : str, default "Angstrom"
        Unit that wave_min/wave_max are expressed in (e.g. "um", "Angstrom").
        Defaults to Angstrom since the database carries a standardized
        rest_wavelength_angstrom column for every row.
    extra_filters : dict, optional
        Filter directly on fields inside the per-row extra_info JSON blob.
        Keys are field names (e.g. "Type", "Reference"). String
        comparisons are case-insensitive; rows missing the field are excluded.
        e.g. extra_filters={"Type": "Emission"} on the SDSS files.
    element : str, optional
        Exact match (case-insensitive) on the coarse 'element' column, e.g.
        "H", "Fe", "H2", "CO", "PAH". This is element/molecule-level only
        (not ionization state) -- see list_elements() to discover what's
        available.
    science_case : str, optional
        Exact match (case-insensitive) on the 'science_case' column, currently
        hardcoded as galactic, nebular, molecular, or stellar.

    Returns
    -------
    astropy.table.Table
        Filtered subset (same columns as db).
    """
    mask = np.ones(len(db), dtype=bool)

    if name_contains is not None:
        mask &= np.char.find(np.char.lower(db["line_name"].astype(str)), name_contains.lower()) >= 0

    if source is not None:
        mask &= db["source_list"] == source

    if element is not None and "element" in db.colnames:
        col = db["element"]
        if hasattr(col, "mask"):
            elem_col = np.array([("" if m else str(v)) for v, m in zip(col, col.mask)])
        else:
            elem_col = np.array([str(v) if v else "" for v in col])
        mask &= np.char.lower(elem_col) == element.lower()

    if wave_min is not None or wave_max is not None:
        std_col = "rest_wavelength_angstrom" if "rest_wavelength_angstrom" in db.colnames else None
        if std_col is not None:
            converted = (np.asarray(db[std_col]) * u.Angstrom).to_value(u.Unit(unit))
        else:
            converted = np.array([
                (row["rest_wavelength"] * u.Unit(row["wavelength_unit"])).to_value(u.Unit(unit))
                for row in db
            ])
        if wave_min is not None:
            mask &= converted >= wave_min
        if wave_max is not None:
            mask &= converted <= wave_max

    if science_case is not None and "science_case" in db.colnames:
        sc_lower = science_case.lower()
        sc_mask = np.zeros(len(db), dtype=bool)
        for i, val in enumerate(db["science_case"]):
            if isinstance(val, (list, tuple)):
                sc_mask[i] = sc_lower in [str(v).lower() for v in val]
            else:
                sc_mask[i] = str(val).lower() == sc_lower
        mask &= sc_mask

    if extra_filters:
        candidate_idx = np.where(mask)[0]
        keep = np.zeros(len(candidate_idx), dtype=bool)
        for i, row_idx in enumerate(candidate_idx):
            extra = get_extra_info(db[row_idx])
            ok = True
            for field, expected in extra_filters.items():
                actual = extra.get(field)
                if actual is None:
                    ok = False
                    break
                if isinstance(actual, str) and isinstance(expected, str):
                    if actual.lower() != expected.lower():
                        ok = False
                        break
                elif actual != expected:
                    ok = False
                    break
            keep[i] = ok

        extra_mask = np.zeros(len(db), dtype=bool)
        extra_mask[candidate_idx[keep]] = True
        mask &= extra_mask

    return db[mask]


def list_elements(db):
    """
    List the distinct element/molecule tags present in the database.

    Returns
    -------
    dict
        Maps element/molecule tag (e.g. "Fe", "H2") -> row count, sorted by
        count descending. Rows the tagger couldn't classify are reported
        separately under the key "(unparsed)".
    """
    from collections import Counter
    col = db["element"]
    if hasattr(col, "mask"):
        vals = ["(unparsed)" if m else str(v) for v, m in zip(col, col.mask)]
    else:
        vals = [str(v) if v else "(unparsed)" for v in col]
    counts = Counter(vals)
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def to_jdaviz_line_list(db_subset, unit="Angstrom"):
    """
    Convert a (subset of the) database into the minimal QTable schema jdaviz's
    Line Lists plugin expects: a 'linename' column and a 'rest' column carrying
    a Quantity.

    Parameters
    ----------
    db_subset : astropy.table.Table
        A (filtered) result from get_lines(), or the full db.
    unit : str, default "Angstrom"
        Unit to express 'rest' in. Uses the precomputed rest_wavelength_angstrom
        column when available and converts from there.

    Returns
    -------
    astropy.table.QTable
        With exactly two columns: 'linename' (str) and 'rest' (Quantity),
        ready to pass to viz.load_line_list().

    """
    from astropy.table import QTable

    target = u.Unit(unit)
    if "rest_wavelength_angstrom" in db_subset.colnames:
        rest = (np.asarray(db_subset["rest_wavelength_angstrom"]) * u.Angstrom).to(target)
    else:
        rest = u.Quantity([
            (row["rest_wavelength"] * u.Unit(row["wavelength_unit"])).to(target)
            for row in db_subset
        ])

    out = QTable()
    out["linename"] = [str(n) for n in db_subset["line_name"]]
    out["rest"] = rest
    return out
