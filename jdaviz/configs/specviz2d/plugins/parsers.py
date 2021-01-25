from glue.core.data import Data

from jdaviz.core.registries import data_parser_registry

from astropy.nddata import CCDData
from spectral_cube import SpectralCube
from specutils import Spectrum1D
from astropy.io import fits
import astropy.units as u
import numpy as np
import logging
from astropy.wcs import WCS
from pathlib import Path

__all__ = ['spec2d_parser']

def _check_is_file(path):
    return isinstance(path, str) and Path(path).is_file()

@data_parser_registry("spec2d-parser")
def spec2d_parser(app, data_obj, data_label=None):
    """
    Attempts to parse a 2D spectrum object.

    Notes
    -----
    This currently only works with JWST-type data in which the data is in the
    second hdu of the fits file.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    # In the case where the data object is a string, attempt to parse it as
    #  a fits file.
    # TODO: this current does not handle the case where the file in the path is
    #  anything but a fits file whose wcs can be extracted.
    def _parse_as_ccddata(path):
        with fits.open(path) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header
            data = data * u.Unit(header['BUNIT'])
            wcs = WCS(header)

        return CCDData(data, wcs=wcs)

    def _parse_as_cube(path):
        with fits.open(path) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header
            if header['NAXIS'] == 2:
                new_data = np.expand_dims(data, axis=1)
                header['NAXIS'] = 3

            header['NAXIS3'] = 1
            header['BUNIT'] = 'dN/s'
            header['CUNIT3'] = 'um'
            wcs = WCS(header)

            meta = {'S_REGION': header['S_REGION']}

        return SpectralCube(new_data, wcs=wcs, meta=meta)

    if _check_is_file(data_obj):
        # data_obj = _parse_as_ccddata(data_obj)
        data_obj = _parse_as_cube(data_obj)

    if data_label is None:
        data_label = f"Spectrum 2D"
    else:
        data_label = "{} 2D".format(data_label)

    app.data_collection[data_label] = data_obj

    print(data_label)
    return data_label

@data_parser_registry("spec2d-1d-parser")
def spec2d_1d_parser(app, data_obj, data_label=None):
    """
    Attempts to parse a 2D spectrum object.

    Notes
    -----
    This currently only works with JWST-type data in which the data is in the
    second hdu of the fits file.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    if _check_is_file(data_obj):
        with fits.open(path) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header

