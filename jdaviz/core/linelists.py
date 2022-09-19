import pkg_resources
import json

from astropy.table import QTable

__all__ = ['get_linelist_metadata', 'get_available_linelists', 'load_preset_linelist']


def get_linelist_metadata():
    """Return metadata for line lists."""
    metadata_file = pkg_resources.resource_filename("jdaviz",
                                                    "data/linelists/linelist_metadata.json")
    with open(metadata_file) as f:
        metadata = json.load(f)
    return metadata


def get_available_linelists():
    """
    Return all available line lists.

    Filters out all entries that do not explicitly contain medium information, as to not
    mislead users
    """
    metadata = get_linelist_metadata()
    return [list for list in list(metadata.keys()) if 'medium' in metadata[list]]


def load_preset_linelist(name):
    """Return one of the preset line lists, loaded into `~astropy.table.QTable`.
    """
    metadata = get_linelist_metadata()
    if name not in metadata.keys():
        raise ValueError("Line name not in available set of line lists. " +
                         "Valid list names are: {}".format(list(metadata.keys())))
    fname_base = metadata[name]["filename_base"]
    fname = pkg_resources.resource_filename("jdaviz",
                                            "data/linelists/{}.csv".format(fname_base))
    units = metadata[name]["units"]
    linetable = QTable.read(fname)

    # Add units
    linetable['Rest Value'].unit = units

    # Add column with list name reference
    linetable['listname'] = name

    # Rename remaining columns
    linetable.rename_columns(('Line Name', 'Rest Value'), ('linename', 'rest'))

    return linetable
