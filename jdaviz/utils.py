import os
from traitlets import Unicode
from astropy.io import fits
from spectral_cube import SpectralCube
from spectral_cube.io.fits import FITSReadError
import logging
import numpy as  np

__all__ = ['load_template']

EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])


def load_template(file_name, path=None, traitlet=True):
    """
    Load a vue template file and instantiate the appropriate traitlet object.

    Parameters
    ----------
    file_name : str
        The name of the template file.
    root_path : str
        The path to where the template file is stored. If none is given,
        assumes the directory where the python file calling this function
        resides.

    Returns
    -------
    `Unicode`
        The traitlet object used to hold the vue code.
    """
    path = os.path.dirname(path)

    with open(os.path.join(path, file_name)) as f:
        TEMPLATE = f.read()

    if traitlet:
        return Unicode(TEMPLATE)

    return TEMPLATE


def parse_data(file_path, data_collection):
    """
    Attempts to parse a data file and auto-populate available viewers in
    cubeviz.

    Parameters
    ----------
    file_path : str
        The path to a cube-like data file.
    data_collection : `~glue.core.DataCollection`
        The application-level data collection into which the parsed data will
        be placed.

    Returns
    -------
    ext_mapping : dict
        A mapping of the three necessary components of the cubeviz viewers to
        the data component labels in glue.
    """
    ext_mapping = {'flux': None,
                   'uncert': None,
                   'mask': None}

    with fits.open(file_path) as hdulist:
        wcs = None

        for hdu in hdulist:
            if hdu.data is None:
                continue

            # This will fail on attempting to load anything that
            # isn't cube-shaped
            try:
                sc = SpectralCube.read(hdu)
                wcs = sc.wcs
            except ValueError:
                # This will fail if the parsing of the wcs does not provide
                # proper celestial axes
                try:
                    hdu.header.update(wcs.to_header())
                    sc = SpectralCube.read(hdu)
                except ValueError as e:
                    logging.error(e)
                    continue
            except FITSReadError as e:
                logging.error(e)
                continue

            data_collection[hdu.name] = sc

            # If the data type is some kind of integer, assume it's the mask/dq
            if hdu.data.dtype in (np.int, np.uint, np.uint32) or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['mask']):
                ext_mapping['mask'] = hdu.name

            if 'errtype' in [x.lower() for x in hdu.header.keys()] or \
                    any(x in hdu.name.lower() for x in EXT_TYPES['uncert']):
                ext_mapping['uncert'] = hdu.name

            if any(x in hdu.name.lower() for x in EXT_TYPES['flux']):
                ext_mapping['flux'] = hdu.name

    return ext_mapping
