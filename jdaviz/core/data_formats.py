import os
import pathlib

import astropy.io
from astropy.io import registry, fits
from astropy.nddata import CCDData
from astropy.wcs import WCS

from specutils.io.registers import identify_spectrum_format
from specutils import Spectrum1D, SpectrumList, SpectrumCollection
from stdatamodels import asdf_in_fits

from jdaviz.core.config import list_configurations

__all__ = [
    'guess_dimensionality',
    'get_valid_format',
    'identify_data',
    'identify_helper'
]

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


def _get_wcs(filename, header):
    """
    Get gwcs.wcs.WCS or astropy.wcs.WCS from FITS file.
    """
    try:
        with asdf_in_fits.open(filename) as af:
            wcs = af.tree['meta']['wcs']

    # if the file doesn't have ASDF-in-FITS, then
    # the 'meta' key doesn't exist, yielding a KeyError:
    except KeyError:
        # fall back on using astropy WCS:
        wcs = WCS(header)

    return wcs


def identify_helper(filename, ext=1):
    """
    Guess the appropriate viz helper for a data file.

    Parameters
    ----------
    filename : str (path-like)
        Name for a local data file.
    ext : int
        Extension from the FITS file.

    Returns
    -------
    helper_name : list of str
        Name of the best-guess compatible helpers for ``filename``.

    Fits HDUList : astropy.io.fits.HDUList
        The HDUList of the file opened to identify the helper
    """
    supported_dtypes = [
        Spectrum1D,
        SpectrumList,
        SpectrumCollection,
        CCDData
    ]

    if filename.lower().endswith('asdf'):
        # ASDF files are only supported in jdaviz for
        # Roman WFI 2D images, so suggest imviz:
        return (['imviz'], None)

    # Must use memmap=False to force close all handles and allow file overwrite
    hdul = fits.open(filename, memmap=False)
    data = hdul[ext]
    header = data.header
    wcs = _get_wcs(filename, header)
    has_spectral_axis = 'spectral' in wcs.world_axis_object_classes

    n_axes = (
        int(has_spectral_axis) +

        sum([component[0] in ['celestial', 'angle']
             for component in wcs.world_axis_object_components]) -

        # remove any slit_frame axis from the count
        (0 if not hasattr(wcs, 'available_frames') else
         int('slit_frame' in wcs.available_frames))
    )

    # use astropy to recognize some data formats:
    possible_formats = {}
    for cls in supported_dtypes:
        fmt = registry.identify_format(
            'read', cls, filename, None, {}, {}
        )
        if fmt:
            possible_formats[cls] = fmt

    # If CCDData is the only match:
    if len(possible_formats) == 1:
        only_key, only_value = possible_formats.popitem()
        if only_key == CCDData:
            # could be 2D spectrum or 2D image. break tie with WCS:
            if has_spectral_axis:
                if n_axes > 1:
                    return (['specviz2d'], hdul)
                return (['specviz'], hdul)
            elif not isinstance(data, fits.BinTableHDU):
                return (['imviz'], hdul)

    # Ensure specviz is chosen when ``data`` is a table or recarray
    # and there's a "known" spectral column name:
    if isinstance(data, (fits.BinTableHDU, fits.fitsrec.FITS_rec)):
        # now catch spectra in FITS tables, looking for
        # columns with "wave" or "flux" in the names:
        table_columns = [getattr(col, 'name', col).lower() for col in data.columns]

        # these are "known" prefixes for column names
        # in FITS tables of spectral observations
        known_spectral_columns = [
            'wave',
            'flux'
        ]

        # this list of bools indicates any
        # spectral column names found:
        found_spectral_columns = [
            found_col.startswith(known_col)
            for known_col in known_spectral_columns
            for found_col in table_columns
        ]

        # if at least one spectral column is found:
        if sum(found_spectral_columns):
            return (['specviz'], hdul)

    # If the data could be spectral:
    for cls in [Spectrum1D, SpectrumList]:
        if cls in possible_formats.keys():
            recognized_spectrum_format = possible_formats[cls][0].lower()

            # first catch known JWST spectrum types:
            if (n_axes == 3 and
                    recognized_spectrum_format.find('s3d') > -1):
                return (['cubeviz'], hdul)
            elif (n_axes == 2 and
                  recognized_spectrum_format.find('x1d') > -1):
                return (['specviz'], hdul)

            # we intentionally don't choose specviz2d for
            # data recognized as 's2d' as we did with the cases above,
            # because 2D data products could be 2D spectra *or* 2D images
            # that the registry recognizes as s2d.

            # Use WCS to break the tie below:
            elif n_axes == 2:
                if has_spectral_axis:
                    return (['specviz2d'], hdul)
                return (['imviz'], hdul)

            elif n_axes == 1:
                return (['specviz'], hdul)

    try:
        # try using the specutils registry:
        valid_format, config = identify_data(filename)
        return ([config], hdul)
    except ValueError:
        # if file type not recognized:
        pass

    if n_axes == 2 and not has_spectral_axis:
        # at this point, non-spectral 2D data are likely images:
        return (['imviz'], hdul)

    raise ValueError(f"No helper could be auto-identified for {filename}.")
