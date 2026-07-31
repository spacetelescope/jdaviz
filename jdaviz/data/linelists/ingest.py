"""
ingest.py
---------
Reads all raw emission-line CSV files in this directory, validates them
against schema.yaml, and merges them into a single consolidated
emission_lines.ecsv database.

Usage:
    python ingest.py

To add a NEW source file later:
    1. Drop the new .csv into this directory.
    2. Add an entry for it under `extra_info_columns_by_file` in schema.yaml
       (rest_wavelength_col, wavelength_unit, and any extra columns to keep).
    3. Re-run `python ingest.py`. It will re-read *all* source files and
       rebuild emission_lines.ecsv from scratch, OR see
       `append_new_file()` below to add just one file to an existing database.
"""

import re
import json
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from astropy.table import Table, vstack
from astropy import units as u

_HERE = Path(__file__).resolve().parent
SCHEMA_FILE = _HERE / "schema.yaml"
OUTPUT_FILE = _HERE / "emission_lines.ecsv"


def load_schema(schema_file=SCHEMA_FILE):
    with open(schema_file, "r") as f:
        return yaml.safe_load(f)


GREEK_TO_NAME = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}

# --- coarse element/molecule extraction ------------------------------------
MOLECULE_PREFIXES = ["H2", "CO", "O2", "CH", "PAH"]

# named hydrogen series / shorthand
HYDROGEN_PATTERNS = [
    re.compile(r'^Ly'),                        # Ly, Ly a, Ly b, Ly d, Ly e, Lyalpha
    re.compile(r'^La\b'),                      # Lyman alpha shorthand
    re.compile(r'^Pa\s*\d'),                   # Pa9, Pa10 ...
    re.compile(r'^Pa\s*[a-z]'),                # Pa d, Pa g, Pa ae
    re.compile(r'^P[dg]\b'),                   # Pd, Pg (Paschen delta/gamma shorthand)
    re.compile(r'^H(alpha|beta|gamma|delta|epsilon|zeta|eta|theta)\b'),  # noqa
    re.compile(r'^H\s?[a-z]\b'),                # Ha/Hb/Hd/He/Hg
    re.compile(r'^H\d{1,2}\b'),                  # H8-H21 numbered Balmer
    re.compile(r'^HI\b'),                        # "HI series limit" safety net
]

_ROMAN = r'(XVIII|XVII|XVI|XIV|XIII|XII|XIX|XX|VIII|VII|IX|VI|III|IV|II|XI|X|V|I)'
ELEMENT_ROMAN_RE = re.compile(r'^\[?([A-Z][a-z]?)\s?' + _ROMAN + r'\b')
PAREN_SPECIES_RE = re.compile(r'\(([A-Z][a-z]?)\s?' + _ROMAN + r'\b')
BARE_ELEMENT_RE = re.compile(r'^[A-Z][a-z]?$')

# single-letter tokens that are ambiguous historical/Fraunhofer shorthand in
# these particular files (SDSS.csv), not reliable element indicators
AMBIGUOUS_BARE_TOKENS = {"G", "K"}


def extract_element(name):
    """
    Best-effort coarse element/molecule tag for a line name, e.g. "Fe", "H",
    "H2", "CO", "PAH". Returns None when the name is too ambiguous to tag
    confidently (e.g. "Sky", bare "G"/"K" Fraunhofer shorthand, or a blended
    feature listed as "Si IV + O I").
    """
    s = name.strip()

    if s in AMBIGUOUS_BARE_TOKENS:
        return None

    for prefix in MOLECULE_PREFIXES:
        if s.startswith(prefix):
            return prefix

    m = PAREN_SPECIES_RE.search(s)
    if m:
        return m.group(1)

    m = ELEMENT_ROMAN_RE.match(s.lstrip("["))
    if m:
        return m.group(1)

    for pat in HYDROGEN_PATTERNS:
        if pat.match(s):
            return "H"

    if BARE_ELEMENT_RE.fullmatch(s):
        return s

    return None
# -----------------------------------------------------------------------


def _clean_value(v):
    """Turn NaN values into None so they drop out of the JSON blob,
    transliterate Greek letters so they survive as distinct, readable names
    instead of being silently deleted, and strip any other stray non-ASCII garbage."""
    if pd.isna(v):
        return None
    if isinstance(v, str):
        for greek, name in GREEK_TO_NAME.items():
            v = v.replace(greek, name)
        v = v.encode("ascii", errors="ignore").decode("ascii")
        v = " ".join(v.split())  # collapse internal tabs/newlines/repeated spaces, strip ends
        if v.count("(") > v.count(")"):
            v = v + ")" * (v.count("(") - v.count(")"))  # fix truncated )'s
        if v == "":
            return None
    return v


def read_one_file(filename, file_schema):
    """Read a single raw CSV into a normalized astropy Table with core
    columns + a JSON 'extra_info' column."""
    df = pd.read_csv(_HERE / filename, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]

    wave_col = file_schema["rest_wavelength_col"]
    unit_str = file_schema["wavelength_unit"]
    extra_cols = file_schema.get("extra_cols", [])
    element_override = file_schema.get("element_override")
    science_case = file_schema.get("science_case", "")  # e.g. galactic, stellar, nebular, molecular

    # validate wavelength column exists and sanity-check the range
    if wave_col not in df.columns:
        raise ValueError(f"{filename}: expected wavelength column '{wave_col}' not found")

    names, waves, extras, sources, elements = [], [], [], [], []
    for _, row in df.iterrows():
        name = _clean_value(row["Line Name"])
        wave = _clean_value(row[wave_col])
        if name is None or wave is None:
            continue

        extra = {}
        for col in extra_cols:
            if col in df.columns:
                val = _clean_value(row[col])
                if val is not None:
                    extra[col] = val

        names.append(str(name))
        waves.append(float(wave))
        extras.append(json.dumps(extra) if extra else "{}")
        sources.append(filename)
        # use "0" (not "") for unresolved elements so the column round-trips as a
        # plain (unmasked) string column -- avoids ECSV masked-column ambiguity
        # and the default astropy fill_value of "N/A" for missing entries
        elements.append(element_override if element_override else (extract_element(str(name)) or "0")) # noqa

    tbl = Table()
    tbl["line_name"] = names
    tbl["rest_wavelength"] = np.array(waves)
    tbl["wavelength_unit"] = [unit_str] * len(names)
    tbl["source_list"] = sources
    tbl["element"] = elements
    tbl["extra_info"] = extras
    tbl["science_case"] = [science_case] * len(names)

    tbl["rest_wavelength"].unit = None
    tbl.meta["source_file_units"] = {filename: unit_str}
    return tbl


def sanity_check(tbl, schema):
    bounds = schema.get("wavelength_sanity_bounds", {})
    for unit_str, (lo, hi) in bounds.items():
        mask = tbl["wavelength_unit"] == unit_str
        bad = mask & ((tbl["rest_wavelength"] < lo) | (tbl["rest_wavelength"] > hi))
        if bad.any():
            bad_rows = tbl[bad]
            print(f"WARNING: {bad.sum()} row(s) with unit '{unit_str}' fall outside "
                  f"expected range [{lo}, {hi}]:")
            print(bad_rows["line_name", "rest_wavelength", "source_list"])


def add_standard_unit_column(master, target_unit="Angstrom"):
    """
    Add a rest_wavelength_<unit> column with every row converted to a single
    common unit, so the database is usable without doing per-row unit math.
    The original rest_wavelength + wavelength_unit columns are kept as-is
    """
    target = u.Unit(target_unit)
    converted = np.array([
        (row["rest_wavelength"] * u.Unit(row["wavelength_unit"])).to_value(target)
        for row in master
    ])
    col_name = f"rest_wavelength_{target_unit.lower().replace(' ', '_')}"
    master[col_name] = converted
    master[col_name].unit = target  # attach unit so QTable.read() returns a Quantity column
    return master, col_name


def deduplicate_line_names(master, angstrom_col):
    """
    For every line_name that appears more than once in *master*, append
    λ{wavelength_in_angstrom_rounded_to_nearest_integer} so that each row
    has a unique label.  E.g. '[O III]' at 4959 Å and 5007 Å become
    '[O III]λ4959' and '[O III]λ5008'.

    Parameters
    ----------
    master : astropy.table.Table
        The merged table (must already contain `angstrom_col`).
    angstrom_col : str
        Name of the column that holds wavelengths in Angstrom.

    Returns
    -------
    master : astropy.table.Table
        Same table with `line_name` values updated in-place for duplicates.
    """
    names = np.array(master["line_name"])
    waves_aa = np.array(master[angstrom_col], dtype=float)

    # find names that appear more than once
    unique, counts = np.unique(names, return_counts=True)
    duplicated = set(unique[counts > 1])

    if not duplicated:
        return master

    # Build as a plain Python list first so there is no fixed-width numpy
    # truncation; we re-create the numpy array with the required dtype at the end.
    new_names = list(names)
    for i, (name, wave) in enumerate(zip(names, waves_aa)):
        if name in duplicated:
            new_names[i] = f"{name} {int(round(wave))}"

    master["line_name"] = np.array(new_names, dtype=object).astype(str)
    n_affected = int((counts[counts > 1] - 0).sum())  # total rows that were renamed
    print(f"Disambiguated {len(duplicated)} non-unique name(s) "
          f"affecting {n_affected} row(s) by appending λ<wavelength_Å>.")
    return master


def build_database(schema_file=SCHEMA_FILE, output_file=OUTPUT_FILE, standard_unit="Angstrom"):
    schema = load_schema(schema_file)
    file_configs = schema["extra_info_columns_by_file"]

    tables = []
    for filename, file_schema in file_configs.items():
        print(f"Reading {filename} ...")
        tbl = read_one_file(filename, file_schema)
        print(f"  -> {len(tbl)} valid rows")
        tables.append(tbl)

    master = vstack(tables, metadata_conflicts="silent")

    master, std_col = add_standard_unit_column(master, target_unit=standard_unit)

    master = deduplicate_line_names(master, std_col)

    master.meta = {
        "description": "Consolidated emission line database",
        "core_columns": schema["core_columns"] + [std_col, "element", "science_case"],
        "note": f"'{std_col}' gives every row's wavelength converted to {standard_unit} "
                "(with an attached astropy unit, so it reads directly into a QTable as a "
                "Quantity column) -- no unit math needed for basic use. "
                "'rest_wavelength' + 'wavelength_unit' preserve the original value exactly "
                "as given in the source file (i.e. original significant figures). "
                "'element' is a best-effort COARSE element/molecule tag (e.g. 'Fe', 'H', "
                "'H2', 'CO', 'PAH') -- not ionization state -- derived from line_name; "
                "it is '0' where the name was too ambiguous to tag confidently. "
                "'science_case' is a coarse per-source-file science-use tag "
                "(e.g. 'galactic', 'stellar', 'nebular', 'molecular'). "
                "'extra_info' is a JSON string of any per-source-file metadata.",
    }

    sanity_check(master, schema)

    master.write(output_file, format="ascii.ecsv", overwrite=True)
    print(f"\nWrote {len(master)} total rows to {output_file} "
          f"(all rows include a '{std_col}' column in addition to their native unit)")
    return master


if __name__ == "__main__":
    build_database()
