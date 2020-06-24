<<<<<<< HEAD

import os
import pathlib

import astropy.io
from specutils.io.registers import identify_spectrum_format
from specutils import Spectrum1D

from jdaviz.core.config import list_configurations


# create a default file format to configuration mapping
default_mapping = {'JWST x1d': 'specviz', 'JWST s2d': 'specviz2d',
                   'JWST s3d': 'cubeviz', 'MaNGA cube': 'cubeviz',
                   'MaNGA rss': 'imviz'}

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
=======
# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: data_formats.py
# Project: core
# Author: Brian Cherinka
# Created: Tuesday, 23rd June 2020 4:41:31 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 23rd June 2020 4:41:32 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from astropy.table import Table
from astropy.utils.data import get_readable_fileobj

import jdaviz.core.data_identifiers as dataid
from jdaviz.core.config import list_configurations


class Base(object):
    @classmethod
    def register(cls):
        '''register the object in the format table '''
        return (cls.fname, cls.config, cls.dimension, cls.identifier)


class JWSTx1D(Base):
    fname = 'JWST x1d'
    config = 'specviz'
    dimension = '1d'
    identifier = 'identify_jwst_x1d_fits'


class BaseImage(Base):
    config = 'imviz'
    dimension = '2d'


class JWSTs2D(BaseImage):
    fname = 'JWST s2d'
    config = 'imviz'
    dimension = '2d'
    identifier = 'identify_jwst_s2d_fits'


class BaseCube(Base):
    config = 'cubeviz'
    dimension = '3d'


class JWSTs3D(BaseCube):
    fname = 'JWST s3d'
    identifier = 'identify_jwst_s3d_fits'


class MangaCube(BaseCube):
    fname = 'MaNGA cube'
    identifier = 'identify_sdss_manga_cube_fits'


# generic formats

class GenericCube(BaseCube):
    fname = 'generic cube'
    identifier = 'identify_generic_cube'


class GenericImage(BaseImage):
    fname = 'generic image'
    identifier = 'identify_generic_fits_image'


def _get_subclasses(base):
    ''' Recursively get all subclasses from a given base class '''
    subs = []
    for cls in base.__subclasses__():
        if cls.__subclasses__():
            subs.extend(_get_subclasses(cls))
        elif hasattr(cls, 'fname'):
            subs.append(cls)
        else:
            pass
    return subs


def get_formats():
    ''' Retrieve the registered list of valid jdaviz formats '''
    tt = Table(names=['format', 'config', 'dimension', 'identifier'],
               dtype=['str', 'str', 'str', 'str'])

    for cls in _get_subclasses(Base):
        tt.add_row(cls.register())

    tt.sort('format')

    return tt


def get_valid_format(filename):
    ''' Identify a best match jdaviz format from a filename '''

    # get a list of all valid formats
    formats = get_formats()

    # identify first available matching format
    valid_format = None
    config = None
    for row in formats:
        # lookup and call the identifier function
        assert hasattr(dataid, row["identifier"]), (f'Identifier {row["identifier"]} missing '
                                                    'definition in from list of functions.')

        idfxn = getattr(dataid, row["identifier"])
        if idfxn(filename):
            valid_format = row['format']
            config = row['config']
            break

    # return the format and config
    return valid_format, config


def identify_data(filename, current=None):
    ''' Identify the data format and application configuration from a filename '''
>>>>>>> eb96e27... adding data valid format identifier and identifier functions

    valid_format, config = get_valid_format(filename)

    # get a list of pre-built configurations
    valid_configs = list_configurations()

    # - check that valid_format exists
    # - check that config is in the list of available configurations
    # - check that config does not conflict with the existing configuration

    if not valid_format:
<<<<<<< HEAD
        raise ValueError('Cannot determine format of the file to load.  Please specify a format')
=======
        raise ValueError('Cannot determine the format of the file to load.  Please specify a format')
>>>>>>> eb96e27... adding data valid format identifier and identifier functions
    elif config not in valid_configs:
        raise ValueError(f"Config {config} not a valid configuration.")
    elif current and config != current:
        raise ValueError('Mismatch between input file format and loaded configuration.')
<<<<<<< HEAD

    return valid_format, config
=======
    else:
        return valid_format, config

>>>>>>> eb96e27... adding data valid format identifier and identifier functions
