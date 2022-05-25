import os
import pathlib

import astropy.io
from specutils.io.registers import identify_spectrum_format
from specutils import SpectrumList

from jdaviz.core.config import list_configurations

__all__ = ['guess_dimensionality', 'get_valid_format', 'identify_data']

# create a default file format to configuration mapping
default_mapping = {'JWST x1d': 'specviz', 'JWST s2d': 'specviz2d',
                   'JWST s3d': 'cubeviz', 'MaNGA cube': 'cubeviz',
                   'MaNGA rss': 'specviz'}

# get formats table for specutils objects
formats_table = astropy.io.registry.get_formats(readwrite='Read')
formats_table.add_index('Data class')
formats_table = formats_table.loc[['Spectrum1D', 'SpectrumList']]
formats_table.sort(['Data class', 'Format'])

file_to_config_mapping = {i: default_mapping.get(
    i, 'specviz') for i in formats_table['Format']}

# default n-dimension to configuration mapping
ndim_to_config_mapping = {1: 'specviz', 2: 'specviz2d', 3: 'cubeviz'}


def guess_dimensionality(filename):
    """Guess the dimensionality of a file.

    Parameters
    ----------
    filename : str or `pathlib.Path` or file-like object
        The filename of the loaded data

    Returns
    -------
    ndim : int
        The number of dimensions of the data
    """

    # check for valid string input
    if not isinstance(filename, (str, pathlib.Path)) or not os.path.isfile(filename):
        raise ValueError(f'{filename} is not a valid string path to a file')

    # get the dimension number of the first extension
    ndim = astropy.io.fits.getval(filename, 'NAXIS', ext=1)
    return ndim


def get_valid_format(filename):
    """Identify a best match Jdaviz configuration from a filename.

    Parameters
    ----------
    filename : str
        The filename of the loaded data

    Returns
    -------
    valid_format : str
        A valid file format
    config : str
        The recommended application configuration
    """

    valid_file_format = identify_spectrum_format(filename, SpectrumList)
    ndim = guess_dimensionality(filename)

    if valid_file_format:
        recommended_config = file_to_config_mapping.get(valid_file_format, 'default')
    else:
        recommended_config = ndim_to_config_mapping.get(ndim, 'default')

    return valid_file_format, recommended_config


def identify_data(filename, current=None):
    """Identify the data format and application configuration from a filename.

    Parameters
    ----------
    filename : str or `pathlib.Path` or file-like object
        The filename of the loaded data
    current : str or `None`
        The currently loading application configuration, if any

    Returns
    -------
    valid_format : str
        A valid file format
    config : str
        The recommended application configuration
    """

    valid_format, config = get_valid_format(filename)

    # get a list of pre-built configurations
    valid_configs = list_configurations()

    # - check that valid_format exists
    # - check that config is in the list of available configurations
    # - check that config does not conflict with the existing configuration

    if not valid_format:
        raise ValueError('Cannot determine format of the file to load.  Please specify a format')
    elif config not in valid_configs:
        raise ValueError(f"Config {config} not a valid configuration.")
    elif current and config != current:
        raise ValueError('Mismatch between input file format and loaded configuration.')

    return valid_format, config
