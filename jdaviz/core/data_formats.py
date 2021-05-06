
import os
import pathlib

import astropy.io
from specutils.io.registers import identify_spectrum_format
from specutils import Spectrum1D

from jdaviz.core.config import list_configurations
from jdaviz.core.events import DataPromptMessage


# create a default file format to configuration mapping
default_mapping = {'JWST x1d': 'specviz', 'JWST s2d': 'specviz2d',
                   'JWST s3d': 'cubeviz', 'MaNGA cube': 'cubeviz',
                   'MaNGA rss': 'imviz'}

# get formats table for specutils objects
formats_table = astropy.io.registry.get_formats(data_class=Spectrum1D,
                                                readwrite='Read')

file_to_config_mapping = {i: default_mapping.get(
    i, 'specviz') for i in formats_table['Format']}

# default n-dimension to configuration mapping
ndim_to_config_mapping = {1: 'specviz', 2: 'specviz2d', 3: 'cubeviz'}


def guess_dimensionality(filename):
    """ Guess the dimensionality of a file.

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
    """ Identify a best match jdaviz configuration from a filename

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

    valid_file_format = identify_spectrum_format(filename)
    ndim = guess_dimensionality(filename)

    if valid_file_format:
        recommended_config = file_to_config_mapping.get(valid_file_format, 'default')
    else:
        recommended_config = ndim_to_config_mapping.get(ndim, 'default')

    return valid_file_format, recommended_config


def identify_data(filename, current=None):
    """ Identify the data format and application configuration from a filename.

    Parameters
    ----------
    filename : str or `pathlib.Path` or file-like object
        The filename of the loaded data
    current : str or ``None``
        The currently loading application configuration, if any

    Returns
    -------
        valid_format : str
            A valid file format
        config : str
            The recommended application configuration
        status : str
            A status message
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


def prompt_data(app, filename):
    ''' Prompt for a data dialog modal
    Given a JDAviz application instance and a data filename, checks
    for a valid file format and recommended configuration and triggers
    the data prompt dialog window with a message.
    Parameters
    ----------
    app : application instance
        The current jdaviz application
    filename : str
        The filename of the loaded data
    '''
    # get the current configuration
    current_config = app.get_configuration().get('settings').get('configuration', 'default')

    # get a valid file format, config, and status
    try:
        valid_format, config = identify_data(filename, current=current_config)
    except ValueError as err:
        status = f'Error: {err}'
        valid_format = ''
        config = ''
    else:
        status = 'Success: Valid Format'
    finally:
        # identify a suggested config
        suggested_format, suggested_config = get_valid_format(filename)


    # get primary header and convert to dict; remove header comments
    hdr = dict(astropy.io.fits.getheader(filename, ext=0))
    hdr.pop('')

    # broadcast a message
    msg = DataPromptMessage(status=status, data_format=valid_format, config=config,
                            current=current_config, suggested_format=suggested_format,
                            suggested_config=suggested_config, filename=filename, hdr=hdr, sender=app)
    app.hub.broadcast(msg)
