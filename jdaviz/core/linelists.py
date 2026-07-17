from importlib import resources
import json
from pathlib import Path

from astropy.table import QTable
import astropy.units as u

__all__ = ['get_linelist_metadata', 'get_available_linelists', 'load_preset_linelist']


def get_linelist_metadata():
    """Return metadata for line lists."""
    metadata_file = resources.files("jdaviz").joinpath("data/linelists/linelist_metadata.json")
    # resources.files returns a Traversable; use read_text to obtain string
    metadata_text = metadata_file.read_text()
    metadata = json.loads(metadata_text)
    return metadata


def get_available_linelists():
    """
    Return all available line lists.

    Filters out all entries that do not explicitly contain medium information, as to not
    mislead users
    """
    metadata = get_linelist_metadata()
    return [name for name in metadata.keys() if 'medium' in metadata[name]]


def load_preset_linelist(name):
    """Return one of the preset line lists, loaded into `~astropy.table.QTable`.
    """
    metadata = get_linelist_metadata()
    if name not in metadata.keys():
        raise ValueError("Line name not in available set of line lists. " +
                         "Valid list names are: {}".format(list(metadata.keys())))

    fname_base = metadata[name]["filename_base"]
    units = metadata[name]["units"]

    # Support multiple file formats for preset lists. Historically most lists
    # were CSV files, but the authoritative/master database is stored as an
    # ECSV (emission_lines.ecsv). Try a set of common suffixes and use the
    # first one that exists.
    data_dir = resources.files("jdaviz").joinpath("data/linelists")
    suffixes = [".csv", ".ecsv", ".ecsv.gz", ".fits", ".txt", ".dat"]
    fname = None
    for s in suffixes:
        candidate = data_dir.joinpath(f"{fname_base}{s}")
        try:
            # pathlib.Path.exists is available on the pathlib-like object returned
            # by resources.files (it is a Traversable), but to be robust convert
            # to str and use Path
            if Path(str(candidate)).exists():
                fname = candidate
                break
        except Exception:
            # If any backend doesn't support direct exists checks, fall back to
            # attempting to read (caught below)
            fname = candidate
            break

    if fname is None:
        # Fallback to the original CSV location to preserve previous behaviour
        fname = data_dir.joinpath(f"{fname_base}.csv")

    # astropy.table.QTable.read will auto-detect ECSV/CSV/FITS based on the
    # filename/contents, so simply call read on the candidate file. If the
    # candidate does not actually exist, this will raise a useful error.
    linetable = QTable.read(fname)

    # Handle the newer 'master' ECSV format which uses different column names
    # (line_name, rest_wavelength, wavelength_unit, rest_wavelength_angstrom).
    # Convert these to the legacy column names expected elsewhere in the code
    # ('Line Name' and 'Rest Value') and attach proper astropy units.
    if 'rest_wavelength' in linetable.colnames:
        # Prefer using per-row wavelength_unit if consistent, otherwise fall
        # back to the rest_wavelength_angstrom column or the metadata units.
        unit_str = None
        if 'wavelength_unit' in linetable.colnames:
            try:
                uniq = set([str(x) for x in linetable['wavelength_unit'] if x is not None])
                if len(uniq) == 1:
                    unit_str = uniq.pop()
            except Exception:
                unit_str = None

        if unit_str is None and 'rest_wavelength_angstrom' in linetable.colnames:
            unit_str = 'Angstrom'

        if unit_str is None:
            unit_str = units

        # Create a Quantity column for the rest wavelength
        try:
            rest_qty = linetable['rest_wavelength'] * u.Unit(unit_str)
        except Exception:
            # Fall back to the provided angstrom column if available
            if 'rest_wavelength_angstrom' in linetable.colnames:
                rest_qty = linetable['rest_wavelength_angstrom'] * u.Angstrom
            else:
                # Last resort: treat numeric values as unitless with metadata unit
                rest_qty = linetable['rest_wavelength'] * u.Unit(units)

        # Insert legacy-style columns
        linetable['Rest Value'] = rest_qty
        linetable['Line Name'] = linetable['line_name']

    # For backwards compatibility with older CSV-based lists, ensure the
    # expected column names exist before proceeding.
    if 'Rest Value' not in linetable.colnames or 'Line Name' not in linetable.colnames:
        raise KeyError(f"Unexpected linelist format for {fname}; expected 'Line Name' and 'Rest Value' columns")

    # Add column with list name reference
    linetable['listname'] = name

    # Rename remaining columns to the internal names used elsewhere
    linetable.rename_columns(('Line Name', 'Rest Value'), ('linename', 'rest'))

    return linetable
