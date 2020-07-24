import pkg_resources
import json
import csv

import astropy.units as u
from astropy.table import QTable

def get_linelist_metadata():
    metadata_file = pkg_resources.resource_filename("jdaviz", "data/linelists/linelist_metadata.json")
    with open(metadata_file) as f:
        metadata = json.load(f)
    return metadata

def get_available_linelists():
    return list(get_linelist_metadata().keys())

def load_preset_linelist(name):
    """
    Returns one of our preset line lists, loaded into an astropy QTable
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

    # Add column with list name refernece
    linetable['listname'] = name

    # Rename remaining columns
    linetable.rename_columns(('Line Name', 'Rest Value'), ('linename', 'rest'))

    return linetable
