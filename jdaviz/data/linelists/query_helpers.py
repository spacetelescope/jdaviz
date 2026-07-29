"""
query_helpers.py
----------------
User-friendly functions for querying and appending to emission_lines.ecsv.

Examples
--------
>>> from query_helpers import load_db, get_lines, get_wavelength_quantity, append_file

>>> db = load_db()
>>> iron_lines = get_lines(db, name_contains="Fe")
>>> nir_lines = get_lines(db, wave_min=1.0, wave_max=2.5, unit="um")
>>> co_lines = get_lines(db, source="CO.csv")

>>> waves = get_wavelength_quantity(iron_lines)   # returns an astropy Quantity

>>> append_file("my_new_linelist.csv", rest_wavelength_col="Rest Value",
...             wavelength_unit="um", extra_cols=["notes"])
"""

import json
import yaml
import numpy as np
import pandas as pd
from astropy.table import Table, vstack
from astropy import units as u
from pathlib import Path

_DIR = Path(__file__).parent

DB_FILE = str(_DIR / "emission_lines.ecsv")
SCHEMA_FILE = str(_DIR / "schema.yaml")


def load_db(db_file=DB_FILE):
    """Load the consolidated database as an astropy Table."""
    return Table.read(db_file, format="ascii.ecsv")


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
        mask &= np.char.lower(db["science_case"].astype(str)) == science_case.lower()

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


def list_extra_fields(db, source=None):
    """
    Discover which extra_info fields actually appear in the database (or in
    one source file), so a UI can offer them as filter options without
    needing to know the schema in advance.

    Parameters
    ----------
    db : astropy.table.Table
        The loaded database.
    source : str, optional
        Restrict the scan to one source_list value, e.g. "SDSS.csv".

    Returns
    -------
    dict
        Maps field name -> sorted list of distinct values seen for that
        field (capped at 20 examples each, to stay usable for a dropdown).
    """
    subset = db if source is None else db[db["source_list"] == source]
    fields = {}
    for row in subset:
        extra = get_extra_info(row)
        for k, v in extra.items():
            seen = fields.setdefault(k, set())
            if len(seen) < 20:
                seen.add(v)
    return {k: sorted(v, key=str) for k, v in fields.items()}


def get_wavelength_quantity(db_subset):
    """
    Convert the rest_wavelength + wavelength_unit columns of a (sub)table
    into a single astropy Quantity array, handling mixed units row-by-row.
    Returned in the unit of the first row if units are mixed; otherwise
    returns them natively.
    """
    if len(db_subset) == 0:
        return u.Quantity([])
    if len(set(db_subset["wavelength_unit"])) == 1:
        unit = u.Unit(db_subset["wavelength_unit"][0])
        return db_subset["rest_wavelength"] * unit
    # mixed units: convert everything to the first row's unit
    target_unit = u.Unit(db_subset["wavelength_unit"][0])
    return u.Quantity([
        (row["rest_wavelength"] * u.Unit(row["wavelength_unit"])).to(target_unit)
        for row in db_subset
    ])


def get_extra_info(row):
    """Parse a row's extra_info JSON string into a plain Python dict."""
    return json.loads(row["extra_info"]) if row["extra_info"] else {}


def plot_lines(db_subset, unit=None, label=True, title=None, figsize=(12, 4),
               color="C0", ax=None, savepath=None):
    """
    Plot a subset of emission lines as a vertical "stick" spectrum, with
    optional line-name labels. Handy for a quick visual sanity-check of a
    query result, e.g. plot_lines(get_lines(db, source="CO.csv")).

    Parameters
    ----------
    db_subset : astropy.table.Table
        A (filtered) table with the standard columns, e.g. from get_lines().
    unit : str, optional
        Unit to plot the x-axis in (e.g. "um" or "Angstrom"). If omitted,
        uses the unit of the first row and converts everything else to it.
    label : bool, default True
        If True, annotate each stick with its line_name (rotated, above the line).
    title : str, optional
        Plot title.
    figsize : tuple, default (12, 4)
        Matplotlib figure size, only used if `ax` is not provided.
    color : str, default "C0"
        Line color for the sticks.
    ax : matplotlib.axes.Axes, optional
        Existing axes to plot into. If None, a new figure/axes is created.
    savepath : str, optional
        If given, save the figure to this path (e.g. "my_lines.png") in
        addition to returning the axes.

    Returns
    -------
    matplotlib.axes.Axes
    """
    import matplotlib.pyplot as plt

    if len(db_subset) == 0:
        raise ValueError("No rows to plot -- the given table/subset is empty.")

    waves = get_wavelength_quantity(db_subset)
    plot_unit = u.Unit(unit) if unit is not None else waves.unit
    waves = waves.to(plot_unit)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    ax.vlines(waves.value, ymin=0, ymax=1, color=color, lw=1.2)

    if label:
        for x, name in zip(waves.value, db_subset["line_name"]):
            ax.text(x, 1.02, str(name), rotation=90, ha="center", va="bottom",
                    fontsize=8, color=color)

    ax.set_ylim(0, 1.6 if label else 1.1)
    ax.set_yticks([])
    ax.set_xlabel(f"Rest wavelength ({plot_unit})")
    ax.set_title(title or f"{len(db_subset)} emission line(s)")
    ax.margins(x=0.02)

    if ax.figure is not None:
        ax.figure.tight_layout()
    if savepath:
        ax.figure.savefig(savepath, dpi=150)

    return ax


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

    Examples
    --------
    >>> from query_helpers import load_db, get_lines, to_jdaviz_line_list
    >>> db = load_db()
    >>> small = get_lines(db, wave_min=6000, wave_max=7000)
    >>> line_list = to_jdaviz_line_list(small)
    >>> viz.load_line_list(line_list)   # in jdaviz
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


def append_file(filename, rest_wavelength_col, wavelength_unit, extra_cols=None,
                 db_file=DB_FILE, schema_file=SCHEMA_FILE):
    """
    Append a new source CSV file to the existing database (and record it
    in schema.yaml so future rebuilds stay reproducible).

    Parameters
    ----------
    filename : str
        Path to the new raw CSV. Must have a "Line Name" column plus a
        wavelength column.
    rest_wavelength_col : str
        Name of the wavelength column in the new file (e.g. "Rest Value").
    wavelength_unit : str
        Astropy-parsable unit string for that column, e.g. "um" or "Angstrom".
    extra_cols : list of str, optional
        Any additional columns to preserve as per-row metadata.
    """
    extra_cols = extra_cols or []

    df = pd.read_csv(filename, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]

    unit = u.Unit(wavelength_unit)  # validates the unit string

    names, waves, extras, sources = [], [], [], []
    for _, row in df.iterrows():
        name = row["Line Name"]
        wave = row[rest_wavelength_col]
        if pd.isna(name) or pd.isna(wave):
            continue
        extra = {c: row[c] for c in extra_cols if c in df.columns and not pd.isna(row[c])}
        names.append(str(name).strip())
        waves.append(float(wave))
        extras.append(json.dumps(extra) if extra else "{}")
        sources.append(filename)

    new_tbl = Table()
    new_tbl["line_name"] = names
    new_tbl["rest_wavelength"] = np.array(waves)
    new_tbl["wavelength_unit"] = [wavelength_unit] * len(names)
    new_tbl["source_list"] = sources
    new_tbl["extra_info"] = extras

    existing = Table.read(db_file, format="ascii.ecsv")
    
    std_cols = [c for c in existing.colnames if c.startswith("rest_wavelength_") and c != "rest_wavelength"]
    if std_cols:
        std_col = std_cols[0]
        target_unit = u.Unit(std_col.replace("rest_wavelength_", ""))
        new_tbl[std_col] = (new_tbl["rest_wavelength"].data * unit).to_value(target_unit)

    merged = vstack([existing, new_tbl], metadata_conflicts="silent")
    merged.meta = existing.meta
    merged.write(db_file, format="ascii.ecsv", overwrite=True)

    # record this file in schema.yaml for reproducibility of future full rebuilds
    with open(schema_file, "r") as f:
        schema = yaml.safe_load(f)
    schema["extra_info_columns_by_file"][filename] = {
        "rest_wavelength_col": rest_wavelength_col,
        "wavelength_unit": wavelength_unit,
        "extra_cols": extra_cols,
    }
    with open(schema_file, "w") as f:
        yaml.safe_dump(schema, f, sort_keys=False)

    print(f"Appended {len(new_tbl)} rows from {filename}. Database now has {len(merged)} rows total.")
    return merged
